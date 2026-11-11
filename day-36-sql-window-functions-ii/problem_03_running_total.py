"""Day 36 - Problem 3: Running total — SUM over the rows so far.

A running total is SUM with the frame ROWS BETWEEN UNBOUNDED
PRECEDING AND CURRENT ROW: every row up to and including this
one. David Kim: $12,000, then $20,000 — and still $20,000 on
Feb 20, because his third order is the pending quote with a NULL
amount and SUM skips NULLs. Final totals: David $20,000,
Frank $29,000, Irene $32,000; company-wide, $81,000.
"""

from __future__ import annotations

import sqlite3


def running_total_per_employee(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int | None, int]]:
    """Every order with its employee's running total to that date."""
    return conn.execute(
        """
        SELECT e.name, o.order_date, o.amount,
               SUM(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS running_total
        FROM orders o
        JOIN employees e ON e.id = o.employee_id
        ORDER BY e.name ASC, o.order_date ASC
        """
    ).fetchall()


def running_total_all_orders(
    conn: sqlite3.Connection,
) -> list[tuple[str, int | None, int]]:
    """Company running total by date: 12,000, 20,000, 35,000,
    40,000, 65,000, 72,000, 72,000 (NULL quote adds nothing),
    81,000."""
    return conn.execute(
        """
        SELECT order_date, amount,
               SUM(amount) OVER (
                   ORDER BY order_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS running_total
        FROM orders
        ORDER BY order_date ASC
        """
    ).fetchall()


def final_totals_per_employee(
    conn: sqlite3.Connection,
) -> list[tuple[str, int]]:
    """Each employee's final running total: David 20,000,
    Frank 29,000, Irene 32,000."""
    rows = running_total_per_employee(conn)
    out: dict[str, int] = {}
    for name, _date, _amount, total in rows:
        out[name] = total
    return sorted(out.items())


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("running per employee:", running_total_per_employee(conn))
    print("running all orders:", running_total_all_orders(conn))
    print("final totals:", final_totals_per_employee(conn))
