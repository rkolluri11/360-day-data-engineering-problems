"""Problem 5 — The streaming rollup
================================

THE PROBLEM (beginner foothold first)
------------------------------------
Problems 1–4 built lists and dicts — fine for thousands of rows. At
10M rows, the intermediate list is the outage. The fix from rung 5:
parentheses stream, brackets build.

    # eager: builds the whole status list, THEN counts
    freq = Counter([e["status"] for e in events])

    # streaming: one item alive at a time, same Counter
    freq = Counter(e["status"] for e in event_stream())

The generator expression feeds Counter one item at a time. Peak
memory is one row plus the tally dict — never the file. The same
pattern rolls up per-user totals over a generator of pairs with
``defaultdict``.

Plain words: the tally board from problem 3, but the ballots arrive
on a conveyor belt and the box never fills up.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A generator is single-pass: run the rollup twice and the second
    run sees zero rows. Re-create the source per pass, or persist
    the (small) result.
  - ``Counter(gen)`` still holds one entry per DISTINCT key. A
    billion distinct user IDs is a billion-entry dict — the rollup
    is O(distinct), not O(rows). For unbounded cardinality, sketch
    it (HyperLogLog) instead of exact-counting.
  - Exceptions surface at the consumer: a malformed row deep in the
    stream raises inside your ``Counter(...)`` call, far from the
    source. Validate at the generator (problem 1's filter pattern)
    so the rollup never sees a bad row.
  - ``islice(source, n)`` caps a stream for sampling — the canonical
    way to peek at an infinite or untrusted source without hanging.

Your solution: ``sampled_status_counts(source, n)`` — Counter of the
first ``n`` statuses pulled from the generator ``source`` (never
materializing more than ``n``). And ``streaming_user_totals(source)``
— per-user float totals over a generator of ``(user, amount)``
pairs, returned as a plain dict.

Plain words: cap the stream, tally what flows, hold nothing extra.

ANALOGY
-------
A turnstile with a counter: people stream through, the number ticks
up, and the hallway never has to hold the whole crowd.

YOUR TASK
---------
Implement ``sampled_status_counts`` and ``streaming_user_totals``
below. Then run the tests: ``python -m pytest tests -q`` from the
day-07 folder.
"""

from collections import Counter, defaultdict
from itertools import islice


def sampled_status_counts(source, n):
    """Counter of the first *n* statuses from generator *source*."""
    return Counter(s for s in islice(source, n))


def streaming_user_totals(source):
    """Per-user float totals over a generator of (user, amount) pairs."""
    totals = defaultdict(float)
    for user, amount in source:
        totals[user] += amount or 0
    return dict(totals)


def infinite_statuses():
    """An endless event source — the rollup must never try to hold it."""
    i = 0
    while True:
        yield "ok" if i % 10 else "fail"
        i += 1


if __name__ == "__main__":
    # 20 pulls from an INFINITE stream — finishes instantly:
    print(sampled_status_counts(infinite_statuses(), 20))
    # Counter({'ok': 18, 'fail': 2})

    def pairs():
        yield ("ada", 10.0)
        yield ("bob", 5.0)
        yield ("ada", 7.5)

    print(streaming_user_totals(pairs()))  # {'ada': 17.5, 'bob': 5.0}
