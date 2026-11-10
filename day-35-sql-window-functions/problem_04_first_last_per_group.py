"""Day 35 - Problem 4: First and last per group — ROW_NUMBER by date.

Top-N is usually about "biggest". The same pattern answers "first"
and "latest": partition by the group, order by the date, keep rn = 1.
First order per employee, latest login per user, earliest event per
device — one shape, different ORDER BY.

Beginner foothold: the ORDER BY inside OVER is the whole question.
ORDER BY order_date ASC asks "first"; ORDER BY order_date DESC asks
"latest". Everything else in the query is identical, which is why
copy-pasting the first version and flipping ASC to DESC is a real
bug vector: check which one you actually wrote.

The edge is David Kim. His first order is order 1 ($12,000, Jan 5);
his latest is order 7, the pending quote with a NULL amount
(Feb 20). "Latest order per employee" returns a NULL amount for
David — correct, and exactly the row a report must not silently
drop or silently treat as zero.
"""

from __future__ import annotations

import sqlite3


def first_order_per_employee(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int | None, str]]:
    """Each employee's first order, by order_date ASC.

    David Kim: order 1, $12,000, 2026-01-05. Frank Lopez: order 3,
    $15,000, 2026-01-20. Irene Novak: order 5, $25,000, 2026-02-10.
    Ordered by employee name.
    """
    return conn.execute(
        """
        SELECT name, order_id, amount, order_date
        FROM (
            SELECT e.name, o.order_id, o.amount, o.order_date,
                   ROW_NUMBER() OVER (
                       PARTITION BY o.employee_id
                       ORDER BY o.order_date ASC
                   ) AS rn
            FROM orders o
            JOIN employees e ON e.id = o.employee_id
        )
        WHERE rn = 1
        ORDER BY name ASC
        """
    ).fetchall()


def latest_order_per_employee(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int | None, str]]:
    """Each employee's latest order, by order_date DESC.

    David Kim: order 7, NULL amount, 2026-02-20 — the pending quote.
    Frank Lopez: order 8, $9,000, 2026-03-01. Irene Novak: order 6,
    $7,000, 2026-02-15. Ordered by employee name.
    """
    return conn.execute(
        """
        SELECT name, order_id, amount, order_date
        FROM (
            SELECT e.name, o.order_id, o.amount, o.order_date,
                   ROW_NUMBER() OVER (
                       PARTITION BY o.employee_id
                       ORDER BY o.order_date DESC
                   ) AS rn
            FROM orders o
            JOIN employees e ON e.id = o.employee_id
        )
        WHERE rn = 1
        ORDER BY name ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("first order per employee: ", first_order_per_employee(conn))
    print("latest order per employee:", latest_order_per_employee(conn))
