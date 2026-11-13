"""Day 38 - Problem 1: NULL is not a value — use IS NULL, never = NULL.

David's Feb 20 order has a NULL amount: a pending quote, not a $0
sale. ``WHERE amount = NULL`` finds 0 rows, always — a comparison
with NULL is UNKNOWN, and WHERE only keeps TRUE. ``IS NULL`` is the
only test that works: it finds exactly 1 order, David's. The same
holds for the org chart: 5 people have no manager.
"""

from __future__ import annotations

import sqlite3


def null_amount_orders(
    conn: sqlite3.Connection,
) -> list[tuple[int, int, str, None, str]]:
    """Orders whose amount is NULL — the pending quotes."""
    return conn.execute(
        """
        SELECT order_id, employee_id, region, amount, order_date
        FROM orders
        WHERE amount IS NULL
        ORDER BY order_id ASC
        """
    ).fetchall()


def equals_null_count(conn: sqlite3.Connection) -> int:
    """Rows matched by ``WHERE amount = NULL`` — always 0."""
    return conn.execute(
        "SELECT COUNT(*) FROM orders WHERE amount = NULL"
    ).fetchone()[0]


def null_managers(conn: sqlite3.Connection) -> list[str]:
    """Employees with no manager: Grace, Irene, Karen, Mia, Nina."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM employees
            WHERE manager_id IS NULL
            ORDER BY name ASC
            """
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("null amount orders:", null_amount_orders(conn))
    print("= NULL matches:", equals_null_count(conn))
    print("no manager:", null_managers(conn))
