"""Day 36 - Problem 4: Moving average — AVG over a sliding window.

A moving average is AVG with a sliding frame: ROWS BETWEEN
2 PRECEDING AND CURRENT ROW is the 3-order average. All orders
by date: Jan 5 $12,000, Jan 12 $10,000, Jan 20 $11,666.67,
Feb 2 $9,333.33, Feb 10 $15,000, Feb 15 $12,333.33,
Feb 20 $16,000, Mar 1 $8,000. Feb 20 is the trap: its window
holds $25,000, $7,000, and a NULL, and AVG averages only the
two real numbers — (25,000 + 7,000) / 2, not / 3.
"""

from __future__ import annotations

import sqlite3


def moving_average_3(
    conn: sqlite3.Connection,
) -> list[tuple[str, int | None, float]]:
    """Every order with its 3-order moving average, all orders by date."""
    return conn.execute(
        """
        SELECT order_date, amount,
               AVG(amount) OVER (
                   ORDER BY order_date
                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
               ) AS ma_3
        FROM orders
        ORDER BY order_date ASC
        """
    ).fetchall()


def moving_average_per_employee(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int | None, float]]:
    """3-order moving average within each employee.

    David: $12,000, $10,000, then $10,000 again — his Feb 20
    window is $12,000, $8,000, NULL, averaged over two numbers.
    Frank: $15,000, $10,000, $9,666.67. Irene: $25,000, $16,000.
    """
    return conn.execute(
        """
        SELECT e.name, o.order_date, o.amount,
               AVG(o.amount) OVER (
                   PARTITION BY o.employee_id ORDER BY o.order_date
                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
               ) AS ma_3
        FROM orders o
        JOIN employees e ON e.id = o.employee_id
        ORDER BY e.name ASC, o.order_date ASC
        """
    ).fetchall()


def cumulative_average(
    conn: sqlite3.Connection,
) -> list[tuple[str, int | None, float]]:
    """Running (cumulative) average by date — the frame is
    UNBOUNDED PRECEDING, so the window only grows. Mar 1:
    $11,571.43 over the seven non-NULL orders."""
    return conn.execute(
        """
        SELECT order_date, amount,
               AVG(amount) OVER (
                   ORDER BY order_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS cum_avg
        FROM orders
        ORDER BY order_date ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("MA3:", moving_average_3(conn))
    print("MA3 per employee:", moving_average_per_employee(conn))
    print("cumulative avg:", cumulative_average(conn))
