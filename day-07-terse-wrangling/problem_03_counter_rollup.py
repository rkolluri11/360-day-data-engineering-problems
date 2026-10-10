"""Problem 3 — The tally sheet
============================

THE PROBLEM (beginner foothold first)
------------------------------------
"How many of each?" is the most-asked question in data work: status
codes per hour, signups per country, errors per service. The manual
version:

    freq = {}
    for e in events:
        s = e["status"]
        if s not in freq:
            freq[s] = 0
        freq[s] += 1

``collections.Counter`` deletes the bookkeeping:

    from collections import Counter
    freq = Counter(e["status"] for e in events)

Hand it any iterable — even a generator — and it tallies in one pass.
``freq.most_common(10)`` is your top-K, sorted, no ``sorted()`` call.

Plain words: tally marks on a whiteboard. Counter holds the marks;
you just call out the values.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Missing keys read as 0 and NEVER raise ``KeyError``. That is a
    feature until a typo'd key silently reports zero instead of
    failing loud. Validate keys when zero is a suspicious answer.
  - ``Counter`` elements must be hashable. Counting dicts or lists
    raises ``TypeError`` — project to a tuple/string key first.
  - ``most_common()`` with no arg returns EVERYTHING sorted — on a
    billion distinct keys that is a sort you did not budget for.
    Pass ``k``.
  - Counter addition/subtraction drops zero and negative counts
    (``c1 - c2`` keeps only positives). If you need the raw math,
    use plain dict arithmetic.

Your solution: ``status_counts(events)`` — a Counter of the
``"status"`` values, accepting any iterable (lists AND generators).
And ``top_k_statuses(events, k)`` — the top-k statuses as a plain
list of ``(status, count)`` pairs, most frequent first.

Plain words: one line for the rollup, one call for the leaderboard.

ANALOGY
-------
Election-night tally board: each ballot is one tick, and
``most_common`` is the anchor reading the leaders off the board.

YOUR TASK
---------
Implement ``status_counts`` and ``top_k_statuses`` below. Then run the
tests: ``python -m pytest tests -q`` from the day-07 folder.
"""

from collections import Counter


def status_counts(events):
    """Return a Counter of ``e["status"]`` over any iterable of events."""
    return Counter(e["status"] for e in events)


def top_k_statuses(events, k):
    """Return the top-k statuses as [(status, count), ...], most first."""
    return status_counts(events).most_common(k)


if __name__ == "__main__":
    events = [{"status": s} for s in
              ["ok"] * 5 + ["retry"] * 2 + ["fail"]]
    print(status_counts(events))        # Counter({'ok': 5, 'retry': 2, 'fail': 1})
    print(top_k_statuses(events, 2))    # [('ok', 5), ('retry', 2)]
    print(status_counts(iter(events)))  # works on generators too
