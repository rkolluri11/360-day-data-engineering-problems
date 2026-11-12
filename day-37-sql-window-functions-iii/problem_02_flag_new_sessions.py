"""Day 37 - Problem 2: Flag new sessions — the 14-day break rule.

A new session starts when the gap since the previous order is over
14 days, or when there is no previous order at all (first order,
gap NULL). Frank's Mar 1 order flags 1; his Feb 2 order flags 0.
The 14 days is a business rule, not in the data — pass a different
threshold and the flags change (see the tests).
"""

from __future__ import annotations

import sqlite3


def flag_new_sessions(
    conn: sqlite3.Connection, gap_threshold_days: int = 14
) -> list[tuple[int, str, int | None, int]]:
    """Every order with 1 when it starts a new session, else 0.

    At the default 14-day threshold: David 1, 0, 1; Frank 1, 0, 1;
    Irene 1, 0. Five sessions start in total.
    """
    return conn.execute(
        """
        SELECT employee_id, order_date, amount,
               CASE WHEN LAG(order_date) OVER (
                       PARTITION BY employee_id ORDER BY order_date
                   ) IS NULL
                   OR CAST(julianday(order_date) - julianday(
                       LAG(order_date) OVER (
                           PARTITION BY employee_id ORDER BY order_date
                       )) AS INTEGER) > ?
               THEN 1 ELSE 0 END AS is_new_session
        FROM orders
        ORDER BY employee_id ASC, order_date ASC
        """,
        (gap_threshold_days,),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("flags (14d):", flag_new_sessions(conn))
    print("flags (30d):", flag_new_sessions(conn, 30))
