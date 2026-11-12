"""Day 37 - Problem 1: Spot the break — gap in days between orders.

Day 36 looked sideways with LAG. Day 37 starts from the same look:
LAG the previous order date per employee, then subtract to get the
gap in days. Frank: 13 days, then 27. David: 7, then 39. Irene: 5.
A first order has no previous date, so its gap is NULL — and a NULL
gap starts a session (Problem 2), it is never zero days.
"""

from __future__ import annotations

import sqlite3


def gaps_between_orders(
    conn: sqlite3.Connection,
) -> list[tuple[int, str, int | None, str | None, int | None]]:
    """Every order with the previous order date and the gap in days.

    Ordered by employee, then date. David: Jan 5 (gap NULL), Jan 12
    (7 days), Feb 20 (39 days). Frank: Jan 20 (NULL), Feb 2 (13),
    Mar 1 (27). Irene: Feb 10 (NULL), Feb 15 (5).
    """
    return conn.execute(
        """
        SELECT employee_id, order_date, amount,
               LAG(order_date) OVER (
                   PARTITION BY employee_id ORDER BY order_date
               ) AS prev_date,
               CAST(julianday(order_date) - julianday(
                   LAG(order_date) OVER (
                       PARTITION BY employee_id ORDER BY order_date
                   )) AS INTEGER) AS gap_days
        FROM orders
        ORDER BY employee_id ASC, order_date ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("gaps:", gaps_between_orders(conn))
