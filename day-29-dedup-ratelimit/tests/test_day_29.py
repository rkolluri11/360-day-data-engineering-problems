"""Day 29 tests: dedup store and rate limiter (interview patterns)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_dedup_store import DedupStore
from problem_02_token_bucket import TokenBucket
from problem_03_sliding_window import SlidingWindowLimiter
from problem_04_ttl_dedup import TTLDedupStore
from problem_05_guarded_pipeline import GuardedPipeline


# --- Problem 1: dedup store ---
def test_dedup_first_wins_repeats_drop():
    store = DedupStore()
    assert store.add("e-1") is True
    assert store.add("e-1") is False
    assert store.add("e-2") is True
    assert store.add("e-1") is False
    assert len(store) == 2


def test_dedup_contains_and_len():
    store = DedupStore()
    store.add("a")
    assert "a" in store
    assert "b" not in store


# --- Problem 2: token bucket ---
def test_bucket_burst_then_empty():
    bucket = TokenBucket(capacity=3, refill_per_second=1.0, now=0.0)
    assert [bucket.allow(0.0) for _ in range(3)] == [True, True, True]
    assert bucket.allow(0.0) is False  # empty, no debt


def test_bucket_refills_over_time_capped_at_capacity():
    bucket = TokenBucket(capacity=2, refill_per_second=1.0, now=0.0)
    assert bucket.allow(0.0) and bucket.allow(0.0)
    assert bucket.allow(0.0) is False
    assert bucket.allow(10.0) is True  # refilled, capped at 2
    assert bucket.allow(10.0) is True
    assert bucket.allow(10.0) is False


def test_bucket_rejects_bad_params():
    import pytest

    with pytest.raises(ValueError):
        TokenBucket(capacity=0, refill_per_second=1.0)
    with pytest.raises(ValueError):
        TokenBucket(capacity=5, refill_per_second=0.0)


# --- Problem 3: sliding window ---
def test_sliding_window_allows_up_to_limit():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10.0)
    assert limiter.allow(0.0) is True
    assert limiter.allow(1.0) is True
    assert limiter.allow(2.0) is False  # at limit


def test_sliding_window_rejects_do_not_count():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10.0)
    assert limiter.allow(0.0) is True
    assert limiter.allow(1.0) is False
    assert limiter.allow(1.0) is False
    assert limiter.count(1.0) == 1  # rejects never recorded


def test_sliding_window_ages_out():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10.0)
    assert limiter.allow(0.0) is True
    assert limiter.allow(1.0) is True
    assert limiter.allow(2.0) is False
    # At t=10.5 the cutoff is 0.5: t=0 aged out, t=1 still inside.
    assert limiter.allow(10.5) is True
    assert limiter.count(10.5) == 2


# --- Problem 4: TTL dedup ---
def test_ttl_dedup_drops_within_window():
    store = TTLDedupStore(ttl_seconds=60.0)
    assert store.add("e-1", 0.0) is True
    assert store.add("e-1", 30.0) is False
    assert store.add("e-1", 59.0) is False


def test_ttl_dedup_expires_after_window():
    store = TTLDedupStore(ttl_seconds=60.0)
    assert store.add("e-1", 0.0) is True
    assert store.add("e-1", 61.0) is True  # aged out, new again
    assert len(store) == 1  # old entry evicted, new one tracked


def test_ttl_dedup_bounded_memory():
    store = TTLDedupStore(ttl_seconds=10.0)
    for i in range(5):
        assert store.add(f"e-{i}", float(i)) is True
    # All five first-seen times are within [0, 4]; at t=20 all expired.
    assert store.add("e-new", 20.0) is True
    assert len(store) == 1


# --- Problem 5: guarded pipeline ---
def test_pipeline_dedup_before_rate_limit():
    pipe = GuardedPipeline(bucket_capacity=1, refill_per_second=1.0)
    assert pipe.submit("k", "e-1", 0.0) == "processed"
    assert pipe.submit("k", "e-1", 0.0) == "duplicate"  # free drop
    assert pipe.submit("k", "e-2", 0.0) == "rate_limited"  # bucket empty
    # The duplicate did not consume a token: after refill, e-2 retries clean.
    assert pipe.submit("k", "e-2", 1.0) == "processed"


def test_pipeline_per_key_buckets():
    pipe = GuardedPipeline(bucket_capacity=1, refill_per_second=1.0)
    assert pipe.submit("a", "e-1", 0.0) == "processed"
    assert pipe.submit("a", "e-2", 0.0) == "rate_limited"
    assert pipe.submit("b", "e-3", 0.0) == "processed"  # own bucket


def test_pipeline_unique_count():
    pipe = GuardedPipeline(bucket_capacity=10, refill_per_second=10.0)
    pipe.submit("k", "e-1", 0.0)
    pipe.submit("k", "e-1", 0.0)
    pipe.submit("k", "e-2", 0.0)
    assert pipe.unique_events() == 2
