"""Problem 8 — The key that changed after filing
=============================================

THE PROBLEM (beginner foothold first)
------------------------------------
You want per-partition counters keyed by (region, currency):

    state = {}
    state[("us", "USD")] = 42        # tuple key: works

But a teammate "simplifies" it:

    state[["us", "USD"]] = 42        # list key: TypeError: unhashable

Plain words: dict keys must be hashable — frozen at birth. A list
can still change shape tomorrow, so Python refuses to file anything
under it.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The streaming job keeps per-partition watermark state in a dict
keyed by a composite partition label. After a refactor, the label
is built as a list. The job crashes at 2 AM with "unhashable type:
'list'" — but only on partitions whose label builder took the new
code path, so it looks like bad data, not a code bug, and the
on-call burns an hour on the wrong trail.

The subtler variant is worse: a mutable object used as part of a
key gets mutated *after* insertion. The entry is still in the dict,
but no lookup can find it again — the label on the folder changed
after filing, so the folder is lost in the cabinet forever.

Your solution: ``composite_key`` always returns a ``tuple`` — an
immutable, hashable snapshot. ``group_by_key`` builds groups keyed
by those tuples, so keys can never drift after insertion.

Plain words: write the address in ink, not pencil. Once the folder
is filed, its label cannot change out from under it.

ANALOGY
-------
Filing folders labeled in permanent marker (tuple) versus pencil
(list): erase and rewrite a pencil label after filing and the folder
is lost — the cabinet still holds it, but nobody can find it again.
"""

from __future__ import annotations


def composite_key(*parts):
    """Build an immutable, hashable composite key from parts.

    Always a tuple: frozen at birth, safe as a dict key, and equal
    keys hash equally no matter where they were built.
    """
    return tuple(parts)   # ink, not pencil


def group_by_key(rows, key_fields):
    """Group rows into a dict keyed by an immutable tuple of fields.

    ``key_fields`` names the columns forming the composite key, e.g.
    ``("region", "currency")``. Groups map ``(region, currency)`` ->
    list of rows, and the keys can never mutate after insertion.
    """
    groups = {}
    for row in rows:
        key = composite_key(*(row[field] for field in key_fields))
        groups.setdefault(key, []).append(row)  # file the row by its ink label
    return groups


if __name__ == "__main__":
    # --- Small example you can trace by hand ---------------------------
    events = [
        {"region": "us", "currency": "USD", "amount": 10.0},
        {"region": "eu", "currency": "EUR", "amount": 20.0},
        {"region": "us", "currency": "USD", "amount": 5.0},
    ]
    groups = group_by_key(events, ("region", "currency"))
    for key, rows in groups.items():
        print(key, "->", len(rows), "rows; key type:", type(key).__name__)

    # --- The trap this prevents ----------------------------------------
    try:
        {["us", "USD"]: 1}          # list as a key: refused at the door
    except TypeError as exc:
        print("list key rejected:", exc)

    k1 = composite_key("us", "USD")
    k2 = composite_key("us", "USD")
    print("equal keys, one hash:", k1 == k2, hash(k1) == hash(k2))
