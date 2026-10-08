"""Problem 7 — The join that stopped scanning
===========================================

THE PROBLEM (beginner foothold first)
------------------------------------
Each order carries a ``product_id``; a separate catalog lists every
product's name and category:

    orders  = [{"order_id": 1, "product_id": "p9"}, ...]
    catalog = [{"product_id": "p9", "name": "Cable"}, ...]

To attach the product name to each order, the beginner code loops
the catalog *inside* the order loop — for every order, scan every
catalog row until the id matches.

Plain words: to label 1,000 parcels you walk the warehouse and read
every shelf label, once per parcel.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The nightly enrichment job processes 500,000 orders against a
20,000-SKU catalog. The nested loop costs O(orders x SKUs): 10
billion comparisons a night. The job creeps from 20 minutes to 6
hours, misses the warehouse cutoff, and the morning dashboard shows
yesterday's numbers — again.

Worse, one night a SKU is missing from the catalog feed. The scan
finds nothing, the order is silently dropped, and revenue is
under-reported until finance notices a week later.

Your solution: ``build_lookup`` indexes the catalog into a ``dict``
once — O(SKUs). ``enrich_facts`` then resolves each order with a
single O(1) dict lookup, so the whole job is O(orders + SKUs).
Orders whose SKU is missing are kept and marked with an explicit
``default`` instead of being dropped.

Plain words: build the phone book once, then look up each name in
one flip. A missing name gets a clear "UNKNOWN" stamp — never a
quiet disappearance.

ANALOGY
-------
Looking up every phone number by reading the directory cover to
cover (nested scan) versus building the alphabetical index once and
flipping straight to each name (dict lookup).
"""

from __future__ import annotations


def build_lookup(dimension_rows, key):
    """Index dimension rows into a dict keyed by ``key``.

    One O(n) pass up front buys O(1) lookups forever after. If the
    same key appears twice, the later row wins (last-write-wins,
    like a slowly-changing dimension reload).
    """
    lookup = {}
    for row in dimension_rows:
        lookup[row[key]] = row     # index it once, find it in one flip
    return lookup


def enrich_facts(fact_rows, lookup, fact_key, default=None):
    """Left-join facts to a prebuilt dict lookup.

    Every fact row is kept. When its key is missing from the lookup,
    the row is enriched with ``default`` and flagged — nothing is
    silently dropped.
    """
    enriched = []
    for fact in fact_rows:
        dim = lookup.get(fact[fact_key], default)  # one hash lookup
        enriched.append({**fact, "dim": dim})       # copy fact + enrichment
    return enriched


if __name__ == "__main__":
    # --- Small example you can trace by hand ---------------------------
    catalog = [
        {"sku": "p1", "name": "USB Cable", "category": "Accessories"},
        {"sku": "p2", "name": "Keyboard", "category": "Peripherals"},
    ]
    orders = [
        {"order_id": 101, "sku": "p1", "qty": 2},
        {"order_id": 102, "sku": "p9", "qty": 1},   # missing from catalog
        {"order_id": 103, "sku": "p2", "qty": 1},
    ]

    lookup = build_lookup(catalog, "sku")
    for row in enrich_facts(orders, lookup, "sku",
                            default={"name": "UNKNOWN", "category": "UNKNOWN"}):
        print(row)
    # order 102 survives with the UNKNOWN stamp instead of vanishing
