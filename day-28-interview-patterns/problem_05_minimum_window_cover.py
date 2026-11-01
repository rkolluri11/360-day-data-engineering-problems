"""Problem 5 — the shortest run covering every required event type.

THE PROBLEM (beginner foothold first)
------------------------------------
A log must contain one of each required event type — "login",
"checkout", "receipt" — before a session counts as complete. The
question is the shortest contiguous run that covers them all: any
longer run wastes investigation time, and a run missing one type
does not count at all.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The classic minimum-window-substring shape, generalized from
    characters to any hashable event type, in O(n) with two hashmaps
    (required counts, window counts) and a "formed" counter — no
    O(n^2) rescanning, and no re-checking the whole requirement set
    on every step.
  - Required types may repeat in the log; extras are fine — the
    window only has to *contain* each required type at least once.
  - When the left edge advances past a required type that was present
    exactly once, the window stops covering and the search continues;
    it does not restart.
  - Impossible is a normal answer: when some required type never
    appears, the result is ``None``, not an empty window pretending
    to cover. An empty requirement set returns the empty window
    ``(0, -1, [])`` — vacuously covered, honestly reported.

Plain words: expand until every required type is inside, then shrink
from the left until it just barely still is — the smallest such
window is the answer.
"""

from typing import Hashable, Iterable, List, Optional, Tuple


def minimum_window_cover(
    events: List[Hashable], required: Iterable[Hashable]
) -> Optional[Tuple[int, int, List[Hashable]]]:
    """Return ``(start, end_inclusive, window)`` of the shortest
    contiguous run of ``events`` containing every distinct item in
    ``required`` at least once, or ``None`` if impossible.
    """
    required_set = set(required)
    if not required_set:
        return (0, -1, [])
    if not events:
        return None
    window_counts = {}
    formed = 0
    left = 0
    best = None  # (length, start, end)
    for right, event in enumerate(events):
        if event in required_set:
            window_counts[event] = window_counts.get(event, 0) + 1
            if window_counts[event] == 1:
                formed += 1
        while formed == len(required_set):
            length = right - left + 1
            if best is None or length < best[0]:
                best = (length, left, right)
            left_event = events[left]
            if left_event in required_set:
                window_counts[left_event] -= 1
                if window_counts[left_event] == 0:
                    formed -= 1
            left += 1
    if best is None:
        return None
    _, start, end = best
    return (start, end, list(events[start:end + 1]))
