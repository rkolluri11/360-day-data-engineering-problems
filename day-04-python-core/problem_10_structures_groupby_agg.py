"""Problem 10 — The rollup without the KeyError chain
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Count orders per region:

    counts = {}
    for row in rows:
        region = row["region"]
        if region not in counts:     # the KeyError guard, every time
            counts[region] = 0
        counts[region] += 1

It works, but nesting it two levels deep (region -> currency ->
stats) turns into a pyramid of ``if ... not in`` guards that is
easy to get wrong and painful to read.

Plain words: before filing each letter you check whether the
pigeonhole exists, build it if not, then file — for every letter.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The hourly revenue rollup aggregates the firehose into
``region -> currency -> {orders, revenue}``. A hand-rolled nested
version missed one guard on the currency level: the first EUR row
after a deploy raised ``KeyError: 'EUR'`, the hourly job died, and
the 9 AM business review opened on a dashboard missing an hour of
European revenue.

``revenue_rollup`` builds the nested structure with ``setdefault``:
each level creates its bucket on first touch, so the "does the
pigeonhole exist?" check can never be forgotten. ``top_region_by_
revenue`` then answers the question the business actually asks —
which region made the most money this hour — straight from the
nested structure.

Plain words: pigeonholes that build themselves the first time a
letter arrives. You can never forget to build one, because you
never build them by hand.

ANALOGY
-------
A mailroom where each pigeonhole assembles itself the moment its
first letter arrives (setdefault) versus a mailroom where the clerk
must remember to nail up every hole before sorting (manual guards).
The self-building mailroom cannot lose mail to a forgotten nail.
"""

from __future__ import annotations


def revenue_rollup(rows):
    """Roll orders up into nested ``{region: {currency: stats}}``.

    ``stats`` is ``{"orders": count, "revenue": total}``.
    ``setdefault`` creates each bucket on first touch, so no level
    can ever raise KeyError on a first-seen key.
    """
    rollup = {}
    for row in rows:
        region_bucket = rollup.setdefault(row["region"], {})
        stats = region_bucket.setdefault(
            row["currency"], {"orders": 0, "revenue": 0.0}
        )
        stats["orders"] += 1
        stats["revenue"] += row["amount"]
    return rollup


def top_region_by_revenue(rollup):
    """Return ``(region, total_revenue)`` for the top region.

    Totals span every currency inside the region. Returns ``None``
    for an empty rollup instead of crashing.
    """
    totals = {
        region: sum(bucket["revenue"] for bucket in currencies.values())
        for region, currencies in rollup.items()
    }
    if not totals:
        return None
    return max(totals.items(), key=lambda pair: pair[1])


if __name__ == "__main__":
    # --- Small example you can trace by hand ---------------------------
    orders = [
        {"region": "us", "currency": "USD", "amount": 100.0},
        {"region": "eu", "currency": "EUR", "amount": 80.0},
        {"region": "us", "currency": "USD", "amount": 50.0},
        {"region": "eu", "currency": "USD", "amount": 20.0},
        {"region": "apac", "currency": "JPY", "amount": 9000.0},
    ]
    rollup = revenue_rollup(orders)
    for region, currencies in rollup.items():
        print(region, "->", currencies)
    print("top region:", top_region_by_revenue(rollup))
    print("empty rollup:", top_region_by_revenue({}))
