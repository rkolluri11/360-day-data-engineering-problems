"""Day 38 - Problem 4: Aggregates skip NULLs.

COUNT(*) counts 8 orders; COUNT(amount) counts 7 known amounts.
SUM(amount) is $81,000, but AVG(amount) is $11,571.43 — over the 7
known amounts, not 8. COALESCE(amount, 0) first makes the average
$10,125 over all 8. Same table, three different "averages": pick
the one that matches the business question, and say which you
picked. David: 3 orders, COUNT(amount) 2, SUM $20,000, AVG $10,000.
"""

from __future__ import annotations

import sqlite3


def order_aggregates(conn: sqlite3.Connection) -> tuple[int, int, int, float, float]:
    """(COUNT(*), COUNT(amount), SUM, AVG(amount), AVG(COALESCE))."""
    return conn.execute(
        """
        SELECT COUNT(*), COUNT(amount), SUM(amount),
               AVG(amount), AVG(COALESCE(amount, 0))
        FROM orders
        """
    ).fetchone()


def per_employee_aggregates(
    conn: sqlite3.Connection,
) -> list[tuple[int, int, int, int | None, float | None]]:
    """Per employee: orders, priced orders, total, average."""
    return conn.execute(
        """
        SELECT employee_id, COUNT(*), COUNT(amount),
               SUM(amount), AVG(amount)
        FROM orders
        GROUP BY employee_id
        ORDER BY employee_id ASC
        """
    ).fetchall()


def single_null_total(conn: sqlite3.Connection) -> int | None:
    """SUM over only NULL amounts is NULL, not zero (Day 37's lesson)."""
    return conn.execute(
        """
        SELECT SUM(amount) FROM orders
        WHERE employee_id = 6 AND order_date = '2026-02-20'
        """
    ).fetchone()[0]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("orders:", order_aggregates(conn))
    print("per employee:", per_employee_aggregates(conn))
    print("single NULL total:", single_null_total(conn))
