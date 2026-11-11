"""Day 36 - Problem 2: Change vs previous — subtract the LAG.

"Sales fell" is a LAG question: this order minus the previous
order for the same employee, in date order. Frank Lopez: $15,000
on Jan 20, then $5,000 on Feb 2 — change -$10,000 (-66.67%);
then $9,000 on Mar 1 — change +$4,000 (+80%). The first order
per employee has no previous row, so LAG is NULL and the change
is NULL — not zero, not a fall. A NULL amount (David's pending
quote) also makes the change NULL.
"""

from __future__ import annotations

import sqlite3


def order_changes(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int | None, int | None, int | None, float | None]]:
    """Every order with its previous amount, change, and % change.

    Ordered by employee, then date. David Kim: Jan 5 $12,000
    (prev NULL, change NULL), Jan 12 $8,000 (prev $12,000,
    change -$4,000, -33.33%), Feb 20 NULL (prev $8,000, NULL).
    """
    return conn.execute(
        """
        SELECT e.name, o.order_date, o.amount,
               LAG(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
               ) AS prev_amount,
               o.amount - LAG(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
               ) AS change_vs_previous,
               ROUND(100.0 * (o.amount - LAG(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
               )) / LAG(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
               ), 2) AS pct_change
        FROM orders o
        JOIN employees e ON e.id = o.employee_id
        ORDER BY e.name ASC, o.order_date ASC
        """
    ).fetchall()


def largest_drop(
    conn: sqlite3.Connection,
) -> tuple[str, str, int | None, int | None, int]:
    """The single biggest order-to-order fall: Irene Novak, -$18,000.

    Feb 10 $25,000 to Feb 15 $7,000. The 2 AM story's alert —
    and the reason the running total in Problem 3 matters beside it.
    """
    rows = [r for r in order_changes(conn) if r[4] is not None]
    return min(rows, key=lambda r: r[4])[:5]  # type: ignore[return-value]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("order changes:", order_changes(conn))
    print("largest drop:", largest_drop(conn))
