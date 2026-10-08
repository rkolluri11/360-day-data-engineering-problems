"""Problem 17 — The lookup that scanned a million rows per join
=========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You have a list of ``(customer_id, tier)`` pairs and you want a dict
so you can look customers up instantly:

    pairs = [("c1", "gold"), ("c2", "silver")]
    lookup = {}
    for cid, tier in pairs:
        lookup[cid] = tier

Plain words: turn a phone book printed as a list into an actual
phone book you can flip open by name. A dict comprehension does it
in one line:

    {cid: tier for cid, tier in pairs}

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Every night your job enriches 2 million order rows with the
customer's *latest* shipping address, which lives in a separate
address-history table: one customer, many address rows, each stamped
with ``updated_at``. The original enrichment code did this per order:

    for order in orders:
        addr = max((a for a in addresses
                    if a["customer_id"] == order["customer_id"]),
                   key=lambda a: a["updated_at"])   # O(addresses) per order!

That is a full scan of the address history for EVERY order —
2M orders x 500K addresses. The job never finished; it was killed
after 6 hours still "enriching".

Your solution: ``build_latest_index(records, key, ts_field)`` — one
dict comprehension (over a timestamp-sorted source) that builds a
``customer_id -> latest record`` index ONCE, so enrichment becomes
a single O(1) dict lookup per order. Because later entries overwrite
earlier ones in a dict comprehension, sorting oldest-first means
the newest record wins — no ``max()`` scan needed.

Plain words: instead of re-reading the whole filing cabinet for
every letter you need to address, you build the cabinet's index
once, then every letter is one drawer pull.

ANALOGY
-------
Looking up every word in a dictionary by reading the dictionary
front to back each time, versus building the thumb-index tabs once
and opening straight to the word forever after.
"""

from __future__ import annotations


# --- BEFORE: scan-per-lookup ---------------------------------------------
# Plain words: correct, but each lookup walks the whole address list.
# n orders x m addresses = a job that never finishes.

def latest_address_scan(customer_id, addresses):
    """Find one customer's latest address by scanning everything."""
    best = None
    for a in addresses:
        if a["customer_id"] == customer_id:
            if best is None or a["updated_at"] > best["updated_at"]:
                best = a
    return best


# --- AFTER: build the index once, look up forever ------------------------
# Plain words: sort oldest-first, then let the comprehension overwrite.
# The last write for each customer is automatically the newest record.

def build_latest_index(records, key="customer_id", ts_field="updated_at"):
    """Build a {key -> latest record} index in a single pass.

    Records must each carry ``key`` and ``ts_field``. When several
    records share a key, the one with the newest timestamp wins.
    """
    ordered = sorted(records, key=lambda r: r[ts_field])  # oldest first
    return {r[key]: r for r in ordered}  # later (newer) overwrites earlier


def enrich_orders(orders, address_index):
    """Attach each order's latest address via one O(1) lookup."""
    return [
        {**o, "ship_to": address_index.get(o["customer_id"])}
        for o in orders
    ]


if __name__ == "__main__":
    addresses = [
        {"customer_id": "c1", "city": "Austin", "updated_at": "2026-09-01"},
        {"customer_id": "c2", "city": "Denver", "updated_at": "2026-09-05"},
        {"customer_id": "c1", "city": "Dallas", "updated_at": "2026-10-02"},
    ]
    index = build_latest_index(addresses)
    print(index["c1"]["city"])  # Dallas — the newest record won

    orders = [{"order_id": "o1", "customer_id": "c1"},
              {"order_id": "o2", "customer_id": "c9"}]  # unknown customer
    print(enrich_orders(orders, index))
    # c1 gets Dallas; c9 gets None instead of crashing the job
    assert latest_address_scan("c1", addresses) == index["c1"]  # same answer
