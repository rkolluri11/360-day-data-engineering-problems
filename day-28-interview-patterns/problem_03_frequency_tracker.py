"""Problem 3 — frequency counts and the first unique event.

THE PROBLEM (beginner foothold first)
------------------------------------
A stream of event types arrives — "click", "purchase", "click" — and
two questions keep coming up: which event type is first to appear
exactly once, and which types are most frequent? Both are hashmap
questions, and both go wrong the same way: by rescanning the whole
stream for every query.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Counts live in one hashmap, updated once per arrival: ``add`` is
    O(1), and queries never rescan the stream.
  - ``first_unique`` is the earliest-arriving item whose count is
    exactly 1 — arrival order, not alphabetical order, decides it.
    When nothing is unique it returns ``None``, not an exception:
    "no unique event" is a normal state, not a bug.
  - ``top_k`` ranks by count descending, and ties break by first
    arrival — a deterministic order a test (and a dashboard) can rely
    on, never dict-insertion luck.
  - ``counts`` returns a copy: callers can read the map but never
    corrupt the tracker's state through it.

Plain words: one hashmap for counts, one memory of arrival order,
and every question is answered from those two — never a rescan.
"""

from typing import Dict, Hashable, List, Optional


class FrequencyTracker:
    """Streaming frequency counts with first-unique and top-k queries."""

    def __init__(self) -> None:
        self._counts: Dict[Hashable, int] = {}
        self._first_seen: Dict[Hashable, int] = {}
        self._arrivals = 0

    def add(self, item: Hashable) -> None:
        """Record one arrival of ``item``."""
        if item not in self._counts:
            self._counts[item] = 0
            self._first_seen[item] = self._arrivals
        self._counts[item] += 1
        self._arrivals += 1

    def counts(self) -> Dict[Hashable, int]:
        """A copy of the current counts (mutating it changes nothing)."""
        return dict(self._counts)

    def first_unique(self) -> Optional[Hashable]:
        """The earliest-arriving item seen exactly once, or ``None``."""
        uniques = [item for item, n in self._counts.items() if n == 1]
        if not uniques:
            return None
        return min(uniques, key=lambda item: self._first_seen[item])

    def top_k(self, k: int) -> List[Hashable]:
        """The ``k`` most frequent items: count desc, then first-seen.

        ``k <= 0`` returns ``[]``; ``k`` larger than the distinct count
        returns every distinct item, ranked.
        """
        if k <= 0:
            return []
        ranked = sorted(
            self._counts,
            key=lambda item: (-self._counts[item], self._first_seen[item]),
        )
        return ranked[:k]
