"""Day 29 - Problem 2: the token bucket — burst now, steady later.

An API allows 10 requests per second with bursts up to 20. A fixed
counter ("10 per second, reset on the clock") fails both halves: it
rejects a legitimate burst at the boundary and lets a flood through
right after the reset. The token bucket fixes both.

Beginner foothold: imagine a bucket that fills with tokens at a steady
rate and holds at most ``capacity``. Each request spends one token.
Empty bucket means "try later" — no debt, no burst beyond capacity.

The clock is injected so tests can move time without sleeping.
"""

from __future__ import annotations


class TokenBucket:
    """Token-bucket rate limiter with an injectable clock."""

    def __init__(self, capacity: int, refill_per_second: float, now: float = 0.0) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_second <= 0:
            raise ValueError("refill rate must be positive")
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = float(capacity)
        self._now = now
        self._last_refill = now

    def _refill(self, now: float) -> None:
        """Add tokens earned since the last refill, capped at capacity."""
        elapsed = now - self._last_refill
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
            self._last_refill = now

    def allow(self, now: float) -> bool:
        """Spend one token if available. True = request proceeds."""
        self._refill(now)
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def available(self, now: float) -> float:
        """Tokens currently available (after refill to ``now``)."""
        self._refill(now)
        return self.tokens


if __name__ == "__main__":
    bucket = TokenBucket(capacity=5, refill_per_second=1.0, now=0.0)
    for t in [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 2.0]:
        print(f"t={t}: {'allow' if bucket.allow(t) else 'reject'} "
              f"(tokens left: {bucket.available(t):.1f})")
