"""Day 40, problem 1: CASE labels the row.

CASE is an IF inside the query: it looks at each row, picks the first
matching WHEN, and returns that value. The same 8 orders, amounts
$5,000 to $25,000, one still NULL, sort into 3 large, 3 medium,
1 small, 1 pending — no new table, no second pass. The NULL branch
is written down (ELSE 'pending'), not left to chance.
"""

from __future__ import annotations

import sqlite3

TIER_CASE = """CASE
    WHEN amount >= 10000 THEN 'large'
    WHEN amount >= 7000 THEN 'medium'
    WHEN amount IS NOT NULL THEN 'small'
    ELSE 'pending'
END"""


def tier_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many orders land in each tier: large 3, medium 3, small 1, pending 1."""
    rows = conn.execute(
        f"SELECT {TIER_CASE} AS tier, COUNT(*) FROM orders GROUP BY tier"
    ).fetchall()
    return {tier: count for tier, count in rows}


def tier_of_order(conn: sqlite3.Connection, order_id: int) -> str:
    """The tier of one order — e.g. order 5 ($25,000) is 'large', order 7 is 'pending'."""
    row = conn.execute(
        f"SELECT {TIER_CASE} FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    return row[0]


def large_order_ids(conn: sqlite3.Connection) -> list[int]:
    """Order ids in the 'large' tier: 1, 3, 5."""
    rows = conn.execute(
        f"SELECT order_id FROM orders WHERE {TIER_CASE} = 'large' ORDER BY order_id"
    ).fetchall()
    return [r[0] for r in rows]
