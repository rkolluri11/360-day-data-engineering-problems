"""Problem 6 — The dedup that silently ate the SLA
=================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You get a list of click event ids from the website:

    events = ["e1", "e2", "e1", "e3", "e2"]

You need each id exactly once, in the order it first appeared.
The obvious code works on five items:

    unique = []
    for e in events:
        if e not in unique:      # scan the whole list, every time
            unique.append(e)

Plain words: for every new arrival you re-read the entire list of
events you have already seen, asking "have I seen you before?".

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The clickstream now delivers 2 million event ids per hour into the
dedup step. ``e not in unique`` scans a *list*, which costs O(n) per
check — so the whole pass costs O(n^2). At 2 million ids that is on
the order of 2 trillion comparisons. The step that took 4 seconds
on a 10k-row sample now overruns the hourly batch window, the
downstream revenue job starts late, and the 2 AM page says the
pipeline "just got slow" — with no error anywhere in the logs.

Your solution: ``dedup_event_ids`` keeps a ``set`` of ids already
seen. Set membership is O(1) — a hash lookup, not a scan — so the
whole pass is O(n). ``find_duplicate_ids`` uses the same trick to
report ids seen more than once: double-counted clicks quietly
inflate revenue if nobody catches them.

Plain words: stop re-reading the guest list for every arrival. Keep
a stamped index box instead — one glance tells you whether the
stamp is already there.

ANALOGY
-------
Finding a book by walking every shelf (list scan) versus checking
the library catalog (set lookup). Both find the book; only one of
them finishes before closing time.
"""

from __future__ import annotations


def dedup_event_ids(event_ids):
    """Return unique event ids, keeping first-seen order.

    A ``set`` tracks what was already seen, so each membership check
    is O(1) and the whole pass is O(n) instead of O(n^2).
    """
    seen = set()      # the stamped index box: O(1) "seen it?" checks
    unique = []       # output keeps original first-seen order
    for eid in event_ids:
        if eid not in seen:
            seen.add(eid)
            unique.append(eid)
    return unique


def find_duplicate_ids(event_ids):
    """Return ids that appear more than once.

    Each duplicate is reported once, in the order its repeat was
    first detected. Two sets do the bookkeeping: one remembers every
    id seen, the other remembers which duplicates were reported.
    """
    seen = set()
    reported = set()
    duplicates = []
    for eid in event_ids:
        if eid in seen:
            if eid not in reported:   # report each duplicate only once
                reported.add(eid)
                duplicates.append(eid)
        else:
            seen.add(eid)
    return duplicates


if __name__ == "__main__":
    # --- Small example you can trace by hand ---------------------------
    clicks = ["c1", "c2", "c1", "c3", "c2", "c2"]
    print("unique:    ", dedup_event_ids(clicks))      # ['c1', 'c2', 'c3']
    print("duplicates:", find_duplicate_ids(clicks))   # ['c1', 'c2']

    # --- Scale check: 200k ids with heavy duplication ------------------
    import random
    import time

    random.seed(7)
    big = [f"evt-{random.randint(0, 50_000)}" for _ in range(200_000)]
    start = time.perf_counter()
    uniq = dedup_event_ids(big)
    dups = find_duplicate_ids(big)
    elapsed = time.perf_counter() - start
    print(f"200k ids -> {len(uniq)} unique, {len(dups)} duplicated "
          f"in {elapsed:.2f}s (set-based, O(n))")
