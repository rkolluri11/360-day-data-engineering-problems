"""Day 29 - Problem 3: the sliding window — count what actually happened lately.

The token bucket is generous to bursts. Sometimes the rule is stricter:
"at most N requests in any rolling W seconds" — no burst allowance, no
clock-boundary trick. The sliding window counts real timestamps and
drops the ones that aged out.

Beginner foothold: keep a queue of request times. On each new request,
throw away every timestamp older than ``window`` seconds, then count
what remains. Under the limit? Record this request and allow it. At the
limit? Reject without recording — a rejected request must not count
against the next one.
"""

from __future__ import annotations

from collections import deque


class SlidingWindowLimiter:
    """At most ``limit`` requests in any rolling ``window_seconds``."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._times: deque[float] = deque()

    def _evict_old(self, now: float) -> None:
        """Drop timestamps at or beyond the window's trailing edge."""
        cutoff = now - self.window_seconds
        while self._times and self._times[0] <= cutoff:
            self._times.popleft()

    def allow(self, now: float) -> bool:
        """Allow if fewer than ``limit`` requests remain in the window."""
        self._evict_old(now)
        if len(self._times) < self.limit:
            self._times.append(now)
            return True
        return False

    def count(self, now: float) -> int:
        """Requests currently inside the window."""
        self._evict_old(now)
        return len(self._times)


if __name__ == "__main__":
    limiter = SlidingWindowLimiter(limit=3, window_seconds=10.0)
    for t in [0.0, 1.0, 2.0, 3.0, 11.0, 12.0]:
        print(f"t={t}: {'allow' if limiter.allow(t) else 'reject'} "
              f"(in window: {limiter.count(t)})")
