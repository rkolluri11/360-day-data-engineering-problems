"""Problem 2 — The dedup index
===========================

THE PROBLEM (beginner foothold first)
------------------------------------
Two shapes haunt every ingestion job: "have I seen this before?" and
"give me one of each". The rookie version keeps a seen-list:

    seen, unique = [], []
    for r in rows:
        if r["email"] not in seen:      # an O(n) scan, every row
            seen.append(r["email"])
            unique.append(r)

For 1M rows that inner scan runs ~500 billion comparisons — the job
from the 2 AM story. The dict version does it in one pass with O(1)
lookups:

    dedup = {r["email"]: r for r in rows}   # later rows win

A dict IS the seen-set: keys are unique by construction, lookups are
hash-based, and the comprehension builds the whole index in one pass.
The set version answers "which values exist":

    statuses = {r["status"] for r in rows}  # distinct values, no scan

Plain words: stop carrying the guest list on a scroll you re-read for
every guest. Give the bouncer a hash table.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Later wins SILENTLY: the last row per key survives. If your rows
    arrive newest-first, you just kept the oldest. Decide the winner
    before you dedup — sort, or pick ``max`` per group.
  - Keys must be hashable: dicts and lists cannot be keys. Normalize
    to tuples/strings first (``tuple(sorted(r.items()))`` is a
    common canonical key).
  - ``{r["email"]: r for r in rows}`` raises ``KeyError`` on a row
    missing the key. Use ``r.get("email")`` if dirty rows exist —
    but know ``None`` keys then collapse together.

Your solution: ``dedup_by_key(rows, key)`` — one dict per key value,
later rows winning. And ``distinct_values(rows, key)`` — the set of
values seen for ``key``, via a set comprehension.

Plain words: the index and the guest list, built in a single pass.

ANALOGY
-------
A library card catalog vs. re-reading every book spine: the dict
comprehension files each book once; the seen-list re-reads the shelf
for every new arrival.

YOUR TASK
---------
Implement ``dedup_by_key`` and ``distinct_values`` below. Then run the
tests: ``python -m pytest tests -q`` from the day-07 folder.
"""


def dedup_by_key(rows, key):
    """Return {key_value: row} — later rows win on duplicate keys."""
    return {r[key]: r for r in rows}


def distinct_values(rows, key):
    """Return the set of distinct values seen for *key*."""
    return {r[key] for r in rows}


if __name__ == "__main__":
    rows = [
        {"email": "a@x.com", "v": 1},
        {"email": "b@x.com", "v": 2},
        {"email": "a@x.com", "v": 3},   # dup — v:3 wins
    ]
    print(dedup_by_key(rows, "email"))
    # {'a@x.com': {'email': 'a@x.com', 'v': 3}, 'b@x.com': {...}}
    print(distinct_values(rows, "email"))  # {'a@x.com', 'b@x.com'}
