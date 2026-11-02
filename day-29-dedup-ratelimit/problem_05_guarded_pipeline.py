"""Day 29 - Problem 5: the guarded pipeline — dedup first, rate limit second.

Problems 1–4 are parts. Production needs them composed, in the right
order: dedup BEFORE rate limiting. Why? A retry storm of duplicate
events must not burn through the rate budget — duplicates are dropped
for free, and only genuinely new events spend tokens.

Beginner foothold: the pipeline is a two-gate funnel. Gate 1 (dedup)
drops repeats without touching the limiter. Gate 2 (token bucket)
admits new events while tokens remain and rejects the rest. The order
matters in one subtle place: an event is only recorded as "seen" once
it passes the rate limiter. A rejected event is not a failure of the
pipeline — it is the pipeline working — and because it was never
recorded, the caller's retry with the same id can still be admitted
later, and the event is still processed exactly once.

Per-key buckets: each producer key gets its own token bucket so one
noisy tenant cannot starve the others.
"""

from __future__ import annotations

from problem_01_dedup_store import DedupStore
from problem_02_token_bucket import TokenBucket


class GuardedPipeline:
    """Dedup-then-rate-limit pipeline, one token bucket per key."""

    def __init__(self, bucket_capacity: int, refill_per_second: float) -> None:
        self._dedup = DedupStore()
        self._buckets: dict[str, TokenBucket] = {}
        self._capacity = bucket_capacity
        self._refill = refill_per_second

    def _bucket_for(self, key: str, now: float) -> TokenBucket:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(self._capacity, self._refill, now=now)
            self._buckets[key] = bucket
        return bucket

    def submit(self, key: str, event_id: str, now: float) -> str:
        """Return 'processed', 'duplicate', or 'rate_limited'.

        Membership is checked before the limiter (duplicates never
        spend tokens), but an id is only recorded once it is actually
        admitted — a rate-limited event stays retryable.
        """
        if event_id in self._dedup:
            return "duplicate"
        if self._bucket_for(key, now).allow(now):
            self._dedup.add(event_id)
            return "processed"
        return "rate_limited"

    def unique_events(self) -> int:
        """Distinct event ids accepted by the dedup gate so far."""
        return len(self._dedup)


if __name__ == "__main__":
    pipe = GuardedPipeline(bucket_capacity=2, refill_per_second=1.0)
    events = [
        ("tenant-a", "e-1", 0.0),
        ("tenant-a", "e-1", 0.0),  # duplicate: free drop
        ("tenant-a", "e-2", 0.0),  # new: spends a token
        ("tenant-a", "e-3", 0.0),  # new but bucket empty
        ("tenant-b", "e-4", 0.0),  # other tenant: own bucket
        ("tenant-a", "e-3", 2.0),  # retry after refill
    ]
    for key, event_id, t in events:
        print(f"{key} {event_id} @ t={t}: {pipe.submit(key, event_id, t)}")
    print(f"unique events: {pipe.unique_events()}")
