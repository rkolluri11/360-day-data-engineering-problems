"""Day 40, problem 4: CASE sorts by meaning, not alphabet.

ORDER BY a CASE puts the $25,000 order first and the pending quote
last: order ids 1, 3, 5, 2, 6, 8, 4, 7. ORDER BY the tier's name
puts 'pending' before 'small' — order ids 1, 3, 5, 2, 6, 8, 7, 4 —
because the alphabet can't tell a pending quote from a small order.
Sort with a CASE, not a label.
"""

from __future__ import annotations

import sqlite3

TIER_SORT_CASE = """CASE
    WHEN amount IS NULL THEN 4
    WHEN amount >= 10000 THEN 1
    WHEN amount >= 7000 THEN 2
    ELSE 3
END"""


def tier_order_ids(conn: sqlite3.Connection) -> list[int]:
    """Order ids sorted by tier (large, medium, small, pending): [1, 3, 5, 2, 6, 8, 4, 7]."""
    rows = conn.execute(
        f"SELECT order_id FROM orders ORDER BY {TIER_SORT_CASE}, order_id"
    ).fetchall()
    return [r[0] for r in rows]


def alpha_tier_order_ids(conn: sqlite3.Connection) -> list[int]:
    """Order ids sorted by the tier's name: [1, 3, 5, 2, 6, 8, 7, 4] — pending before small."""
    rows = conn.execute(
        """SELECT order_id FROM orders ORDER BY
               CASE
                   WHEN amount >= 10000 THEN 'large'
                   WHEN amount >= 7000 THEN 'medium'
                   WHEN amount IS NOT NULL THEN 'small'
                   ELSE 'pending'
               END, order_id"""
    ).fetchall()
    return [r[0] for r in rows]


def first_by_tier(conn: sqlite3.Connection) -> int:
    """The first order by tier sort: order 1, the $12,000 large order."""
    return tier_order_ids(conn)[0]


def last_by_tier(conn: sqlite3.Connection) -> int:
    """The last order by tier sort: order 7, the pending quote."""
    return tier_order_ids(conn)[-1]
