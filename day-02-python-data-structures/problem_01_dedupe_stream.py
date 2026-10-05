"""Problem 1 — The dedup job that gets slower every day
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A stream of event IDs arrives one at a time:

    "evt-1", "evt-2", "evt-1", "evt-3", ...

Write ``dedupe_stream(events)`` that returns the unique IDs in the
order they were first seen: ``["evt-1", "evt-2", "evt-3"]``.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your dedup job processes 50M events a day. The pipeline tracks seen
IDs in a list, and every ``event_id not in seen`` scans the whole
list — which grows all day. By Friday the job is 6 hours behind, and
nothing changed except the data volume.

Your solution must do O(1) amortized work per event, forever: a
list-scan solution (O(n) per event, O(n^2) total) fails the
performance test no matter how correct it looks on small input.

Plain words: stop searching the shelf slot by slot — ask the magic
bag. Keep a ``set`` for instant "seen this?" checks and a ``list``
only to remember first-seen order.

ANALOGY
-------
A bouncer with a photo album checks every page for each guest and the
line gets slower all night. A bouncer with a guest-list app types the
name and knows instantly — the line moves at the same speed at 2 AM
as at 9 PM.
"""

from __future__ import annotations


def dedupe_stream(events):
    """Return unique event IDs in first-seen order, O(1) amortized per event.

    Uses a set for membership (instant lookup) and a list only to
    preserve order — the list is never scanned for membership.
    """
    seen = set()
    unique = []
    for event_id in events:
        if event_id not in seen:
            seen.add(event_id)
            unique.append(event_id)
    return unique


if __name__ == "__main__":
    demo = ["evt-1", "evt-2", "evt-1", "evt-3", "evt-2", "evt-4"]
    print(dedupe_stream(demo))
