"""Day 36 - Problem 5: Name your frame — ROWS vs RANGE, combined view.

The frame is the whole trick. ROWS counts physical rows; RANGE
counts peers — rows tied on the ORDER BY key. Salaries, highest
first: Bob Martinez and Henry Wong both earn $110,000. With
ROWS, Bob's running salary total is $1,137,000 and Henry's is
$1,247,000. With the default frame (RANGE, peers included),
Bob's is already $1,247,000 — Henry's row was pulled in as his
peer. Same data, different totals, because the frame was never
named. The combined per-order view puts LAG, change, running
total, and moving average in one query, so a single row never
has to stand alone as an alert.
"""

from __future__ import annotations

import sqlite3


def salary_running_rows_vs_range(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int, int]]:
    """Each employee with their running salary total under ROWS
    and under the default RANGE frame, highest salary first."""
    return conn.execute(
        """
        SELECT name, salary,
               SUM(salary) OVER (
                   ORDER BY salary DESC
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS rows_total,
               SUM(salary) OVER (
                   ORDER BY salary DESC
               ) AS range_total
        FROM employees
        ORDER BY salary DESC, name ASC
        """
    ).fetchall()


def order_window_view(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int | None, int | None, int | None, int, float]]:
    """One row per order: amount, previous amount, change,
    running total, and 3-order moving average per employee.

    Irene Feb 15: amount $7,000, prev $25,000, change -$18,000,
    running $32,000, moving average $16,000 — the fall, the
    total, and the trend, side by side.
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
               SUM(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS running_total,
               AVG(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
               ) AS ma_3
        FROM orders o
        JOIN employees e ON e.id = o.employee_id
        ORDER BY e.name ASC, o.order_date ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("ROWS vs RANGE:", salary_running_rows_vs_range(conn))
    print("window view:", order_window_view(conn))
