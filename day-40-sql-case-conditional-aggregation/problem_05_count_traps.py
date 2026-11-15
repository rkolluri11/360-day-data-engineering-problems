"""Day 40, problem 5: two traps — no ELSE means NULL, first WHEN wins.

COUNT(CASE WHEN amount>=10000 THEN 1 END) is 3: the NULLs don't
count. Add ELSE 0 and COUNT says 8, because it counts the zeros
too — the dashboard bug from the 2 AM story (David has 3 big orders,
not 8). And ranges written backwards — >=7000 before >=10000 — put
the $25,000 order in 'medium': 6 medium, 0 large, 1 small. Order
your WHENs strictest first, because CASE stops at the first match.
"""

from __future__ import annotations

import sqlite3


def count_big_no_else(conn: sqlite3.Connection) -> int:
    """Big orders counted with no ELSE: 3 (NULLs from the CASE don't count)."""
    row = conn.execute(
        "SELECT COUNT(CASE WHEN amount >= 10000 THEN 1 END) FROM orders"
    ).fetchone()
    return row[0]


def count_big_else_zero(conn: sqlite3.Connection) -> int:
    """Big orders counted with ELSE 0: 8 — every row counts, zeros included."""
    row = conn.execute(
        "SELECT COUNT(CASE WHEN amount >= 10000 THEN 1 ELSE 0 END) FROM orders"
    ).fetchone()
    return row[0]


def sum_big_with_else_zero(conn: sqlite3.Connection) -> int:
    """SUM with ELSE 0 is fine: the zeros add nothing, so the big total is $52,000."""
    row = conn.execute(
        "SELECT SUM(CASE WHEN amount >= 10000 THEN amount ELSE 0 END) FROM orders"
    ).fetchone()
    return row[0]


def backwards_range_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Ranges backwards (>=7000 first): medium 6, small 1, pending 1 — large 0."""
    rows = conn.execute(
        """SELECT CASE
               WHEN amount >= 7000 THEN 'medium'
               WHEN amount >= 10000 THEN 'large'
               WHEN amount IS NOT NULL THEN 'small'
               ELSE 'pending'
           END AS tier, COUNT(*)
           FROM orders GROUP BY tier"""
    ).fetchall()
    return {tier: count for tier, count in rows}


def correct_range_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Ranges strictest first: large 3, medium 3, small 1, pending 1."""
    rows = conn.execute(
        """SELECT CASE
               WHEN amount >= 10000 THEN 'large'
               WHEN amount >= 7000 THEN 'medium'
               WHEN amount IS NOT NULL THEN 'small'
               ELSE 'pending'
           END AS tier, COUNT(*)
           FROM orders GROUP BY tier"""
    ).fetchall()
    return {tier: count for tier, count in rows}
