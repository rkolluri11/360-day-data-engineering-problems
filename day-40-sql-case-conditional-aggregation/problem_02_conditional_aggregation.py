"""Day 40, problem 2: one pass, both regions.

Conditional aggregation: SUM(CASE WHEN region='East' THEN amount
ELSE 0 END) and the West twin in the same SELECT read the table once
and return both totals — East $54,000, West $27,000, $81,000 overall.
The big orders split East 2 ($37,000) and West 1 ($15,000). Three
separate queries read the table three times and can disagree when
data moves between them.
"""

from __future__ import annotations

import sqlite3


def region_totals(conn: sqlite3.Connection) -> dict[str, int]:
    """Total amount per region in a single pass: East 54000, West 27000."""
    row = conn.execute(
        """SELECT
               SUM(CASE WHEN region = 'East' THEN amount ELSE 0 END),
               SUM(CASE WHEN region = 'West' THEN amount ELSE 0 END)
           FROM orders"""
    ).fetchone()
    return {"East": row[0], "West": row[1]}


def total_amount(conn: sqlite3.Connection) -> int:
    """Total across all orders: $81,000 (the NULL pending quote adds nothing)."""
    row = conn.execute("SELECT SUM(amount) FROM orders").fetchone()
    return row[0]


def big_counts_by_region(conn: sqlite3.Connection) -> dict[str, int]:
    """Big orders (>= $10,000) per region: East 2, West 1."""
    rows = conn.execute(
        """SELECT region, COUNT(CASE WHEN amount >= 10000 THEN 1 END)
           FROM orders GROUP BY region"""
    ).fetchall()
    return {region: count for region, count in rows}


def big_totals_by_region(conn: sqlite3.Connection) -> dict[str, int]:
    """Big-order dollars per region: East 37000, West 15000."""
    rows = conn.execute(
        """SELECT region, SUM(CASE WHEN amount >= 10000 THEN amount ELSE 0 END)
           FROM orders GROUP BY region"""
    ).fetchall()
    return {region: total for region, total in rows}
