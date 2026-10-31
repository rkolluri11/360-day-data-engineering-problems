"""Day 27 tests — Python + Streaming: Kafka / Event Hub patterns.

No network, no real broker, no sleeping: topics are in-memory, the
batcher clock is injectable, and retry delays are reported, not
waited out. Stdlib only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from problem_01_partitioned_topic import PartitionedTopic, TopicError
from problem_02_serialization import (
    SchemaError,
    SchemaRegistry,
    SerializationError,
)
from problem_03_batching import Batcher, BatchError
from problem_04_retries_dlq import (
    DeadLetterQueue,
    PermanentError,
    RetryPolicy,
    TransientError,
    deliver,
)
from problem_05_idempotent_consumer import GapError, IdempotentConsumer


# --- Problem 1: partitioned topic -----------------------------------------

def test_same_key_same_partition_across_instances():
    a = PartitionedTopic(4)
    b = PartitionedTopic(4)
    assert a.partition_for("customer-42") == b.partition_for("customer-42")


def test_unkeyed_round_robins():
    topic = PartitionedTopic(3)
    partitions = [topic.produce(None, i)[0] for i in range(6)]
    assert partitions == [0, 1, 2, 0, 1, 2]


def test_offsets_per_partition_and_ordered_read():
    topic = PartitionedTopic(2)
    # Force both partitions via unkeyed round-robin.
    topic.produce(None, "a")
    topic.produce(None, "b")
    topic.produce(None, "c")
    assert topic.read(0) == [(0, None, "a"), (1, None, "c")]
    assert topic.read(1, from_offset=1) == []
    assert topic.read(0, from_offset=1) == [(1, None, "c")]
    with pytest.raises(TopicError):
        topic.read(2)
    with pytest.raises(TopicError):
        PartitionedTopic(0)


# --- Problem 2: serialization ----------------------------------------------

def _registry():
    reg = SchemaRegistry(max_supported_version=3)
    reg.register(1, ["event_id", "amount"])
    reg.register(2, ["event_id", "amount"])
    return reg


def test_encode_decode_roundtrip_and_unknown_fields_tolerated():
    reg = _registry()
    data = reg.encode({"event_id": "e1", "amount": 10, "new_field": "x"}, 1)
    version, payload = reg.decode(data)
    assert version == 1
    assert payload["event_id"] == "e1"
    assert payload["new_field"] == "x"


def test_missing_required_field_fails_at_encode_and_decode():
    reg = _registry()
    with pytest.raises(SchemaError):
        reg.encode({"event_id": "e1"}, 1)
    import json

    bad = json.dumps({"v": 1, "payload": {"event_id": "e1"}}).encode()
    with pytest.raises(SchemaError):
        reg.decode(bad)


def test_corrupt_and_newer_version_rejected():
    reg = _registry()
    with pytest.raises(SerializationError):
        reg.decode(b"not json at all")
    with pytest.raises(SerializationError):
        reg.decode(b'{"v": 1}')
    import json

    newer = json.dumps({"v": 99, "payload": {}}).encode()
    with pytest.raises(SchemaError):
        reg.decode(newer)
    with pytest.raises(SchemaError):
        reg.encode({"event_id": "e1", "amount": 1}, 99)


# --- Problem 3: batching ----------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_batch_flushes_on_count_limit():
    batcher = Batcher(max_records=3, max_bytes=1000)
    assert batcher.add("a") is None
    assert batcher.add("b") is None
    assert batcher.add("c") is None
    flushed = batcher.add("d")
    assert flushed == ["a", "b", "c"]
    assert batcher.flush() == ["d"]


def test_batch_flushes_on_byte_limit_and_rejects_oversize():
    batcher = Batcher(max_records=100, max_bytes=5)
    assert batcher.add("abc") is None
    flushed = batcher.add("def")
    assert flushed == ["abc"]
    with pytest.raises(BatchError):
        batcher.add("toolongrecord")


def test_flush_partial_and_linger_readiness():
    clock = FakeClock()
    batcher = Batcher(max_records=100, max_bytes=1000, linger_ms=100, clock=clock)
    assert batcher.is_ready() is False
    batcher.add("x")
    assert batcher.is_ready() is False
    clock.now = 0.05
    assert batcher.is_ready() is False
    clock.now = 0.10
    assert batcher.is_ready() is True
    assert batcher.flush() == ["x"]
    assert batcher.flush() == []


# --- Problem 4: retries & DLQ ------------------------------------------------

def test_exponential_backoff_capped():
    policy = RetryPolicy(max_attempts=5, base_delay_ms=100, factor=2, max_delay_ms=250)
    assert [policy.delay_for(i) for i in (1, 2, 3, 4)] == [100, 200, 250, 250]


def test_transient_succeeds_on_retry_then_exhaustion_dead_letters():
    policy = RetryPolicy(max_attempts=3, base_delay_ms=100)
    calls = {"n": 0}

    def flaky(record):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientError("broker hiccup")

    result = deliver(flaky, "ok", policy)
    assert result.success is True and result.attempts == 3
    assert result.delays_ms == [100, 200]

    dlq = DeadLetterQueue()
    result = deliver(lambda r: (_ for _ in ()).throw(TransientError("down")), "bad", policy, dlq)
    assert result.success is False and result.attempts == 3 and len(dlq) == 1
    assert dlq.entries[0]["record"] == "bad"


def test_permanent_goes_straight_to_dlq_and_unknown_propagates():
    policy = RetryPolicy(max_attempts=5, base_delay_ms=100)
    dlq = DeadLetterQueue()

    def bad_record(record):
        raise PermanentError("bad payload")

    result = deliver(bad_record, "x", policy, dlq)
    assert result.success is False and result.attempts == 1 and len(dlq) == 1
    with pytest.raises(RuntimeError):
        deliver(lambda r: (_ for _ in ()).throw(RuntimeError("bug")), "x", policy, dlq)


# --- Problem 5: idempotent consumer ------------------------------------------

def test_duplicate_key_never_reprocessed():
    consumer = IdempotentConsumer()
    assert consumer.consume(0, 0, "p1:1", "first") is True
    assert consumer.consume(0, 0, "p1:1", "first") is False
    assert consumer.processed == ["first"]
    assert consumer.committed_offset(0) == 1


def test_gap_raises_and_failed_handler_leaves_no_trace():
    consumer = IdempotentConsumer()
    with pytest.raises(GapError):
        consumer.consume(0, 1, "p1:2", "skipped")
    attempts = {"n": 0}

    def failing(value):
        attempts["n"] += 1
        raise ValueError("boom")

    with pytest.raises(ValueError):
        consumer.consume(0, 0, "p1:1", "v", handler=failing)
    assert consumer.processed == []
    assert consumer.committed_offset(0) == 0
    # Retry after the failure succeeds and is recorded exactly once.
    assert consumer.consume(0, 0, "p1:1", "v") is True


def test_batch_counts_only_new_records():
    consumer = IdempotentConsumer()
    records = [(0, 0, "a", 1), (0, 1, "b", 2), (0, 1, "b", 2), (0, 2, "c", 3)]
    assert consumer.consume_batch(records) == 3
    assert consumer.processed == [1, 2, 3]


def test_end_to_end_broker_batch_consumer_with_redelivery():
    topic = PartitionedTopic(2)
    batcher = Batcher(max_records=10, max_bytes=1000)
    consumer = IdempotentConsumer()
    produced = []
    for i, value in enumerate(["e1", "e2", "e3"]):
        partition, offset = topic.produce("customer-7", value)
        produced.append((partition, offset, f"prod:{i}", value))
        batcher.add(value)
    assert batcher.flush() == ["e1", "e2", "e3"]
    assert consumer.consume_batch(produced) == 3
    # A crash-restart redelivers the whole batch: effect stays exactly-once.
    assert consumer.consume_batch(produced) == 0
    assert consumer.processed == ["e1", "e2", "e3"]
