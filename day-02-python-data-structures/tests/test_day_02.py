"""Day 2 tests — every solution must pass before the day is committed."""

import random
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_dedupe_stream import dedupe_stream
from problem_02_dedupe_by_fields import dedupe_by_fields
from problem_03_hash_join import hash_join
from problem_04_stable_key import keyed_cache, stable_key
from problem_05_bloom_unique import BloomFilter


# --- Problem 1: dedupe_stream -------------------------------------------

def test_01_dedupe_order_and_correctness():
    events = ["evt-1", "evt-2", "evt-1", "evt-3", "evt-2", "evt-4"]
    assert dedupe_stream(events) == ["evt-1", "evt-2", "evt-3", "evt-4"]
    assert dedupe_stream([]) == []
    assert dedupe_stream(["a", "a", "a"]) == ["a"]


def test_01_dedupe_is_linear_time():
    """150k events must finish fast: a list-scan solution fails this."""
    rng = random.Random(42)
    events = [rng.randrange(100_000) for _ in range(150_000)]
    start = time.perf_counter()
    result = dedupe_stream(events)
    elapsed = time.perf_counter() - start
    assert elapsed < 4.0, f"{elapsed:.1f}s — membership is not O(1)"
    assert result == list(dict.fromkeys(events))  # same first-seen order


# --- Problem 2: dedupe_by_fields -----------------------------------------

def test_02_dedupes_on_fields_not_whole_record():
    records = [
        {"event_id": "e1", "source": "web", "ts": 12},
        {"event_id": "e1", "source": "web", "ts": 19},  # dup on the fields
        {"event_id": "e1", "source": "app", "ts": 12},  # different source
    ]
    result = dedupe_by_fields(records, ["event_id", "source"])
    assert result == [records[0], records[2]]  # original objects, first kept


def test_02_handles_unhashable_field_values():
    records = [
        {"event_id": "e1", "tags": ["click", "signup"], "meta": {"v": 1}},
        {"event_id": "e1", "tags": ["click", "signup"], "meta": {"v": 1}},  # dup
        {"event_id": "e1", "tags": ["signup", "click"], "meta": {"v": 1}},  # order matters
        {"event_id": "e1", "tags": ["click"], "meta": {"v": 1}},
        {"event_id": "e1", "tags": ["click"], "meta": {"v": 2}},
    ]
    result = dedupe_by_fields(records, ["event_id", "tags", "meta"])
    assert result == [records[0], records[2], records[3], records[4]]


def test_02_missing_field_counts_as_none():
    records = [
        {"event_id": "e1"},
        {"event_id": "e1", "source": None},  # same as missing
        {"event_id": "e1", "source": "web"},
    ]
    result = dedupe_by_fields(records, ["event_id", "source"])
    assert result == [records[0], records[2]]


# --- Problem 3: hash_join -------------------------------------------------

def test_03_inner_join_correctness():
    orders = [
        {"order_id": 1, "customer_id": "c9", "total": 40},
        {"order_id": 2, "customer_id": "c3", "total": 15},
        {"order_id": 3, "customer_id": "c0", "total": 99},  # no match
    ]
    customers = [
        {"customer_id": "c9", "name": "Asha"},
        {"customer_id": "c3", "name": "Ben"},
        {"customer_id": "c7", "name": "No Orders"},  # no match
    ]
    result = hash_join(orders, customers, "customer_id")
    assert result == [
        {"order_id": 1, "customer_id": "c9", "total": 40, "name": "Asha"},
        {"order_id": 2, "customer_id": "c3", "total": 15, "name": "Ben"},
    ]


def test_03_duplicate_keys_produce_combinations():
    left = [{"k": "x", "a": 1}]
    right = [{"k": "x", "b": 2}, {"k": "x", "b": 3}]
    result = hash_join(left, right, "k")
    assert result == [
        {"k": "x", "a": 1, "b": 2},
        {"k": "x", "a": 1, "b": 3},
    ]


def test_03_join_is_linear_time():
    """30k x 30k must finish fast: a nested-loop join fails this."""
    n = 30_000
    left = [{"id": i, "lv": i * 2} for i in range(n)]
    right = [{"id": i, "rv": i * 3} for i in range(n)]
    start = time.perf_counter()
    result = hash_join(left, right, "id")
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"{elapsed:.1f}s — join is not linear"
    assert len(result) == n
    assert result[1234] == {"id": 1234, "lv": 2468, "rv": 3702}


# --- Problem 4: stable_key / keyed_cache ----------------------------------

def test_04_equal_args_give_equal_hashable_keys():
    k1 = stable_key({"region": "eu", "tags": ["x", "y"]}, [1, 2], mode="fast")
    k2 = stable_key({"tags": ["x", "y"], "region": "eu"}, [1, 2], mode="fast")
    assert k1 == k2
    hash(k1)  # must not raise


def test_04_kwarg_order_ignored():
    assert stable_key(a=1, b=2) == stable_key(b=2, a=1)
    assert stable_key(a=1, b=2) != stable_key(a=1, b=3)


def test_04_cache_runs_once_for_equal_unhashable_args():
    calls = {"n": 0}

    @keyed_cache
    def fetch(filters, columns=("a",)):
        calls["n"] += 1
        return dict(filters)

    r1 = fetch({"region": "eu", "tags": ["x"]}, columns=["a", "b"])
    r2 = fetch({"tags": ["x"], "region": "eu"}, columns=("a", "b"))
    assert calls["n"] == 1
    assert r1 == r2 == {"region": "eu", "tags": ["x"]}
    fetch.cache_clear()
    fetch({"region": "eu", "tags": ["x"]})
    assert calls["n"] == 2


# --- Problem 5: BloomFilter ------------------------------------------------

def test_05_formula_sizing():
    bloom = BloomFilter(capacity=1000, error_rate=0.01)
    # m = -(1000 * ln(0.01)) / ln(2)^2 -> 9586 bits; k -> 7 hashes
    assert bloom.size == 9586
    assert bloom.num_hashes == 7
    assert len(bloom.bits) == 1199


def test_05_no_false_negatives_and_bounded_false_positives():
    n = 20_000
    bloom = BloomFilter(capacity=n, error_rate=0.01)
    for i in range(n):
        bloom.add(f"user-{i}")
    # No false negatives, ever.
    assert all(f"user-{i}" in bloom for i in range(n))
    # False positives stay near the target rate.
    false_hits = sum(1 for i in range(n, 2 * n) if f"user-{i}" in bloom)
    assert false_hits / n < 0.03, f"fp rate {false_hits / n:.3f} too high"


def test_05_memory_is_fixed():
    bloom = BloomFilter(capacity=100_000, error_rate=0.01)
    size_before = len(bloom.bits)
    for i in range(50_000):
        bloom.add(f"user-{i}")
    assert len(bloom.bits) == size_before  # ten items or ten million: same bytes
    assert size_before < 128 * 1024  # ~120 KB for 100k users at 1% fp
