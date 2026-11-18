"""Day 42, problem 2: UNION ALL — stacking channels without losing sales.

Online orders and store orders live in separate tables with the same
shape, and the monthly revenue report stacks them. UNION ALL is the
right stack: 8 rows, $86,000. UNION looks tidier — 7 rows, $81,000 —
and quietly deletes a real sale: Frank Lopez bought $5,000 of
product on 2026-02-02 online AND in store. Same customer, same
amount, same day, two genuine purchases. UNION cannot tell a
legitimate duplicate from a double-counted row, so it deletes one.

That is the production rule: use UNION ALL whenever each row is an
event that really happened. Reach for UNION only when the rows are
supposed to describe a set — and even then, prove the duplicates
you are dropping are actually duplicates, with a GROUP BY ...
HAVING COUNT(*) > 1 check like the one below.
"""

from __future__ import annotations

import sqlite3


def online_total(conn: sqlite3.Connection) -> tuple[int, int]:
    """Online orders: 4 rows, $57,000."""
    return conn.execute("SELECT COUNT(*), SUM(amount) FROM online_orders").fetchone()


def store_total(conn: sqlite3.Connection) -> tuple[int, int]:
    """Store orders: 4 rows, $29,000."""
    return conn.execute("SELECT COUNT(*), SUM(amount) FROM store_orders").fetchone()


def stacked_union_all(conn: sqlite3.Connection) -> tuple[int, int]:
    """UNION ALL stack: 8 rows, $86,000 — every real purchase kept."""
    return conn.execute(
        "SELECT COUNT(*), SUM(amount) FROM ("
        "SELECT customer, amount, order_date FROM online_orders "
        "UNION ALL SELECT customer, amount, order_date FROM store_orders)"
    ).fetchone()


def stacked_union(conn: sqlite3.Connection) -> tuple[int, int]:
    """UNION stack: 7 rows, $81,000 — one $5,000 sale silently deleted."""
    return conn.execute(
        "SELECT COUNT(*), SUM(amount) FROM ("
        "SELECT customer, amount, order_date FROM online_orders "
        "UNION SELECT customer, amount, order_date FROM store_orders)"
    ).fetchone()


def lost_revenue(conn: sqlite3.Connection) -> int:
    """Revenue UNION deletes vs UNION ALL keeps: $5,000."""
    union_all_total = stacked_union_all(conn)[1]
    union_total = stacked_union(conn)[1]
    return union_all_total - union_total


def duplicated_stacked_rows(conn: sqlite3.Connection) -> list[tuple[str, int, str, int]]:
    """(customer, amount, date, times) appearing more than once in the stack.

    Only one tuple repeats: Frank Lopez, $5,000, 2026-02-02, twice —
    and both copies are real purchases, so this is a UNION ALL case,
    not a dedup case.
    """
    rows = conn.execute(
        "SELECT customer, amount, order_date, COUNT(*) AS n FROM ("
        "SELECT customer, amount, order_date FROM online_orders "
        "UNION ALL SELECT customer, amount, order_date FROM store_orders) "
        "GROUP BY customer, amount, order_date HAVING COUNT(*) > 1"
    ).fetchall()
    return [tuple(r) for r in rows]


def stacked_rows_by_date(conn: sqlite3.Connection) -> list[tuple[str, int, str]]:
    """All 8 stacked purchases in date order — the UNION ALL result, kept whole."""
    rows = conn.execute(
        "SELECT customer, amount, order_date FROM online_orders "
        "UNION ALL SELECT customer, amount, order_date FROM store_orders "
        "ORDER BY order_date"
    ).fetchall()
    return [tuple(r) for r in rows]
