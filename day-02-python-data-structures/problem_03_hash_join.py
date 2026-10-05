"""Problem 3 — The join that scanned the shelf
=============================================

THE PROBLEM (beginner foothold first)
------------------------------------
You have two lists of dicts — orders and customers — and you want the
inner join on ``customer_id``:

    orders    = [{"order_id": 1, "customer_id": "c9", "total": 40}, ...]
    customers = [{"customer_id": "c9", "name": "Asha"}, ...]

Write ``hash_join(left, right, key)`` returning one merged dict per
matching pair (``{**left_row, **right_row}`` — right wins on clashing
field names), dropping rows with no match on either side.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The naive join is a nested loop: for every order, scan every
customer. 50k orders x 50k customers is 2.5 billion comparisons —
the job never finishes. Your solution must build a dict index on
**one** side (O(n) build, O(1) lookups) and probe it with the other
side, so the whole join is linear. Duplicate keys on the right side
must produce every combination (a real join, not a lookup).

Plain words: don't walk the shelf for every single question. Build
the labeled-drawers cabinet once, then every lookup is instant.

ANALOGY
-------
Looking up 50,000 phone numbers by re-reading the whole phone book
each time vs. using the index at the back: same answers, one finishes
before lunch, the other finishes next week.
"""

from __future__ import annotations


def hash_join(left, right, key):
    """Inner join two iterables of dicts on ``key`` using a dict index.

    Builds the index on ``right`` (the build side), probes with
    ``left``. Duplicate keys on the right produce every combination.
    Merged rows are ``{**left_row, **right_row}``. Rows missing the
    key or with no match are dropped.
    """
    index = {}
    for row in right:
        index.setdefault(row[key], []).append(row)

    joined = []
    for left_row in left:
        matches = index.get(left_row[key])
        if matches:
            for right_row in matches:
                joined.append({**left_row, **right_row})
    return joined


if __name__ == "__main__":
    orders = [
        {"order_id": 1, "customer_id": "c9", "total": 40},
        {"order_id": 2, "customer_id": "c3", "total": 15},
        {"order_id": 3, "customer_id": "c0", "total": 99},  # no match: dropped
    ]
    customers = [
        {"customer_id": "c9", "name": "Asha"},
        {"customer_id": "c3", "name": "Ben"},
    ]
    for row in hash_join(orders, customers, "customer_id"):
        print(row)
