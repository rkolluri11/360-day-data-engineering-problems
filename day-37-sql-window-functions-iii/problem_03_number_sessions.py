"""Day 37 - Problem 3: Number the islands — running SUM of the flag.

The session number is a running total of the is_new_session flag:
SUM(flag) OVER (PARTITION BY employee ORDER BY date ROWS BETWEEN
UNBOUNDED PRECEDING AND CURRENT ROW). Frank's orders become
sessions 1, 1, 2. David's become 1, 1, 2. Irene's are both 1.
Name the frame: the default RANGE frame would pull tied peers
into the count, so ROWS is spelled out.
"""

from __future__ import annotations

import sqlite3


def number_sessions(
    conn: sqlite3.Connection, gap_threshold_days: int = 14
) -> list[tuple[int, str, int | None, int]]:
    """Every order with its session number within its employee.

    At the default 14-day threshold there are 5 sessions in total:
    David 1, 1, 2; Frank 1, 1, 2; Irene 1, 1.
    """
    return conn.execute(
        """
        WITH flagged AS (
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
        )
        SELECT employee_id, order_date, amount,
               SUM(is_new_session) OVER (
                   PARTITION BY employee_id ORDER BY order_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS session_no
        FROM flagged
        ORDER BY employee_id ASC, order_date ASC
        """,
        (gap_threshold_days,),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("sessions:", number_sessions(conn))
