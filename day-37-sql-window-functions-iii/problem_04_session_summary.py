"""Day 37 - Problem 4: Collapse each island — the session summary.

GROUP BY employee and session number: start, end, order count,
total, and span in days. Frank session 1: Jan 20–Feb 2, 2 orders,
$20,000. Session 2: Mar 1 alone, $9,000. Irene's single session:
Feb 10–15, $32,000. David's second session is one order with a
NULL amount — its total is NULL, not zero, because SUM skips NULLs
and there is nothing else to sum.
"""

from __future__ import annotations

import sqlite3


def session_summary(
    conn: sqlite3.Connection, gap_threshold_days: int = 14
) -> list[tuple[int, int, str, str, int, int | None, int]]:
    """One row per session: start, end, order count, total, span.

    At the default 14-day threshold: 5 sessions. David (6, 1):
    Jan 5–12, 2 orders, $20,000, 7 days. David (6, 2): Feb 20
    alone, 1 order, total NULL, 0 days. Frank (7, 1): Jan 20–
    Feb 2, 2 orders, $20,000, 13 days. Frank (7, 2): Mar 1
    alone, $9,000. Irene (8, 1): Feb 10–15, 2 orders, $32,000,
    5 days.
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
        ),
        numbered AS (
            SELECT *, SUM(is_new_session) OVER (
                PARTITION BY employee_id ORDER BY order_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS session_no
            FROM flagged
        )
        SELECT employee_id, session_no,
               MIN(order_date) AS session_start,
               MAX(order_date) AS session_end,
               COUNT(*) AS orders, SUM(amount) AS total,
               CAST(julianday(MAX(order_date))
                    - julianday(MIN(order_date)) AS INTEGER) AS span_days
        FROM numbered
        GROUP BY employee_id, session_no
        ORDER BY employee_id ASC, session_no ASC
        """,
        (gap_threshold_days,),
    ).fetchall()


def longest_session(
    conn: sqlite3.Connection, gap_threshold_days: int = 14
) -> tuple[int, int, str, str, int, int | None, int]:
    """The single longest session by span in days.

    At 14 days: Frank session 1, Jan 20–Feb 2, 13 days.
    """
    rows = session_summary(conn, gap_threshold_days)
    return max(rows, key=lambda r: (r[6], r[5] if r[5] is not None else -1))


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("sessions:", session_summary(conn))
    print("longest:", longest_session(conn))
    print("sessions (30d):", session_summary(conn, 30))
