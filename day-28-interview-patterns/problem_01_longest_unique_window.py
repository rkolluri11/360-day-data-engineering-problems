"""Problem 1 — the longest run with no repeats.

THE PROBLEM (beginner foothold first)
------------------------------------
Given a stream of events, find the longest stretch where no event
repeats: in "abcabcbb" the answer is "abc" (length 3), because the
fourth character repeats an earlier one and breaks the stretch.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A naive "try every start, extend until a repeat" scan is O(n^2):
    on a million-event log it never finishes. This must run in O(n).
  - When a repeat appears, the window does NOT restart from scratch:
    it jumps its left edge to just past the previous occurrence of
    that event — everything before that point is unrecoverable, but
    everything after it is still a valid, longer candidate.
  - The answer is the window itself, not just its length: a pipeline
    that only reports "3" cannot show anyone which three events.
  - Empty input is a real input: it returns length 0 and an empty
    window, not an error.

Plain words: slide a window, remember where you last saw each event,
and when one repeats, move the left edge past its last sighting.
"""

from typing import Tuple


def longest_unique_window(text: str) -> Tuple[int, str]:
    """Return ``(length, window)`` of the longest substring of ``text``
    with no repeated character.

    Runs in O(n) time with a last-seen hashmap. ``text`` must be a
    string; anything else raises ``TypeError``.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    last_seen = {}
    left = 0
    best_start = 0
    best_length = 0
    for right, char in enumerate(text):
        previous = last_seen.get(char)
        if previous is not None and previous >= left:
            left = previous + 1
        last_seen[char] = right
        if right - left + 1 > best_length:
            best_length = right - left + 1
            best_start = left
    return best_length, text[best_start:best_start + best_length]
