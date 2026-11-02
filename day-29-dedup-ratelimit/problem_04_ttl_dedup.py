"""Day 29 - Problem 4: dedup with an expiry date — memory is not infinite.

Problem 1's store grows forever: every id ever seen stays in memory.
In production that is a slow leak that eventually kills the process.
Real dedup windows are bounded — "have I seen this id in the last hour?"
— so entries must expire.

Beginner foothold: same idea as the sliding window, but for ids instead
of counts. Each id carries the time it was first seen. An id counts as
a duplicate only while its first-seen time is still inside the window;
once it ages out, the same id is new again (a genuine re-send after an
hour is not the same retry storm as three copies in one second).

The window is swept lazily — only on ``add``/``__contains__`` — so an
idle store costs nothing.
"""

from __future__ import annotations


class TTLDedupStore:
    """Dedup within a rolling window; ids expire after ``ttl_seconds``."""

    def __init__(self, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl must be positive")
        self.ttl_seconds = ttl_seconds
        self._first_seen: dict[str, float] = {}

    def _evict_expired(self, now: float) -> None:
        """Drop ids whose first-seen time fell out of the window."""
        cutoff = now - self.ttl_seconds
        expired = [eid for eid, seen_at in self._first_seen.items() if seen_at <= cutoff]
        for eid in expired:
            del self._first_seen[eid]

    def add(self, event_id: str, now: float) -> bool:
        """True if ``event_id`` is new inside the window (and remember it)."""
        self._evict_expired(now)
        if event_id in self._first_seen:
            return False
        self._first_seen[event_id] = now
        return True

    def __contains__(self, event_id: str) -> bool:
        # Membership without a clock cannot evict; callers that need
        # expiry should use add() with an explicit time.
        return event_id in self._first_seen

    def __len__(self) -> int:
        return len(self._first_seen)


if __name__ == "__main__":
    store = TTLDedupStore(ttl_seconds=60.0)
    for event_id, t in [("e-1", 0.0), ("e-1", 30.0), ("e-1", 61.0), ("e-2", 61.0)]:
        print(f"{event_id} @ t={t}: "
              f"{'process' if store.add(event_id, t) else 'drop (duplicate)'}")
    print(f"ids currently tracked: {len(store)}")
