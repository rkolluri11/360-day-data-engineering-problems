"""Problem 4 — Labeled bins
==========================

THE PROBLEM (beginner foothold first)
------------------------------------
Grouping rows by a key is a daily job: orders per customer, events per
service, clicks per campaign. The manual version checks the shelf
before every putaway:

    groups = {}
    for r in rows:
        k = r["user"]
        if k not in groups:      # the key-check, every single row
            groups[k] = []
        groups[k].append(r)

``collections.defaultdict`` hands you a fresh bin the moment a new key
shows up — the check disappears:

    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[r["user"]].append(r)   # bin created on first touch

Same trick for running totals: ``defaultdict(float)`` starts every
new key at ``0.0`` so ``+=`` just works.

Plain words: labeled bins on a conveyor belt. A new label appears,
a new bin is already underneath it.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The factory runs on READ too: ``groups["typo"]`` CREATES the key
    with an empty list. A lookup typo silently grows your dict.
    Use a plain dict (or ``.get``) when reads must not mutate.
  - Match the factory to the type: ``defaultdict(int)`` with float
    amounts truncates silently — ``defaultdict(float)`` for money.
  - Each key gets its OWN fresh bin — ``defaultdict(list)`` never
    shares one list across keys. But ``defaultdict([])`` (an
    instance, not a factory) shares ONE list everywhere: always pass
    the callable, ``list``, not ``[]``.
  - ``json.dumps`` chokes on defaultdict — convert with ``dict()``
    before serializing or shipping downstream.

Your solution: ``group_by(rows, key)`` — {key_value: [rows]} via
``defaultdict(list)``, returned as a plain dict. And
``sum_by(rows, key, field)`` — {key_value: total} via
``defaultdict(float)``, missing fields counting as 0.

Plain words: bins for the rows, bins for the running totals.

ANALOGY
-------
Mailroom sorting slots: the first letter for a new department
conjures its slot into existence — nobody checks whether the slot
is there first.

YOUR TASK
---------
Implement ``group_by`` and ``sum_by`` below. Then run the tests:
``python -m pytest tests -q`` from the day-07 folder.
"""

from collections import defaultdict


def group_by(rows, key):
    """Group rows by *key* — returns a plain dict of lists."""
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return dict(groups)


def sum_by(rows, key, field):
    """Sum *field* per *key* — returns a plain dict of floats."""
    totals = defaultdict(float)
    for r in rows:
        totals[r[key]] += r.get(field) or 0
    return dict(totals)


if __name__ == "__main__":
    rows = [
        {"user": "ada", "amt": 10.0},
        {"user": "bob", "amt": 5.0},
        {"user": "ada", "amt": 7.5},
        {"user": "ada"},                      # missing amt -> 0
    ]
    print(group_by(rows, "user").keys())  # dict_keys(['ada', 'bob'])
    print(sum_by(rows, "user", "amt"))    # {'ada': 17.5, 'bob': 5.0}
