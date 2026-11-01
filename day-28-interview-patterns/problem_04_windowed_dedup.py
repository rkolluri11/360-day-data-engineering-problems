"""Problem 4 — dedup, but only inside a sliding window.

THE PROBLEM (beginner foothold first)
------------------------------------
A producer retries, so the same event arrives twice. A dedup store
that remembers every event id forever grows without bound — and a
store that remembers nothing lets every retry through.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The store remembers only the last ``window_size`` *accepted*
    items: a duplicate inside that window is dropped, and a repeat
    that arrives after the window has slid past it is accepted again.
    Memory is bounded by the window, by construction.
  - Dropping a duplicate must NOT refresh its position in the window:
    a dropped retry does not extend the item's lifetime, or a steady
    stream of retries would pin an item in the window forever.
  - ``window_size`` must be a positive integer; 0 or negative is a
    caller bug and raises ``ValueError``.
  - ``accepted`` reports only what got through, in arrival order —
    the audit trail a downstream consumer actually needs.

Plain words: remember the last N things you let through, drop repeats
of those, and let anything older through again.
"""

from collections import deque
from typing import Deque, Hashable, List


class WindowDeduper:
    """Bounded dedup: duplicates within the last ``window_size``
    accepted items are dropped; older repeats pass again.
    """

    def __init__(self, window_size: int) -> None:
        if not isinstance(window_size, int) or isinstance(window_size, bool):
            raise ValueError("window_size must be a positive integer")
        if window_size < 1:
            raise ValueError("window_size must be at least 1")
        self.window_size = window_size
        self._window: Deque[Hashable] = deque(maxlen=window_size)
        self._accepted: List[Hashable] = []

    def offer(self, item: Hashable) -> bool:
        """Return ``True`` and accept ``item`` if it is not a duplicate
        inside the current window; otherwise drop it and return
        ``False``. Dropped items do not touch the window.
        """
        if item in self._window:
            return False
        self._window.append(item)
        self._accepted.append(item)
        return True

    def accepted(self) -> List[Hashable]:
        """All accepted items, in arrival order (a copy)."""
        return list(self._accepted)
