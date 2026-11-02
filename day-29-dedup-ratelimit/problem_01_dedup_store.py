"""Day 29 - Problem 1: the dedup store — seen it once, never process it twice.

An upstream system retries a batch and your pipeline sees the same event
three times. Without dedup you triple-count revenue. ``DedupStore`` keeps
every id it has accepted and answers one question: is this new?

Beginner foothold: it is a set with a memory. ``add`` returns True the
first time an id appears and False every time after — the caller only
processes the event when ``add`` says True.
"""

from __future__ import annotations


class DedupStore:
    """Exact dedup: first occurrence wins, every repeat is dropped."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def add(self, event_id: str) -> bool:
        """Return True if ``event_id`` is new (and remember it).

        Returns False for any id already seen — the caller must skip
        the event.
        """
        if event_id in self._seen:
            return False
        self._seen.add(event_id)
        return True

    def __contains__(self, event_id: str) -> bool:
        return event_id in self._seen

    def __len__(self) -> int:
        return len(self._seen)


if __name__ == "__main__":
    store = DedupStore()
    for event in ["e-1", "e-2", "e-1", "e-3", "e-2"]:
        print(f"{event}: {'process' if store.add(event) else 'drop (duplicate)'}")
    print(f"unique events kept: {len(store)}")
