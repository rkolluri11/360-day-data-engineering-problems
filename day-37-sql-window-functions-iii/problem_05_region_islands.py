"""Day 37 - Problem 5: The other island shape — consecutive regions.

Islands are about *consecutive* runs, not totals. Frank's regions
are West, West, East — two islands, not one West total. The trick
is a row-number difference: overall row number minus the row number
within the region stays constant inside an island and jumps when
the value changes. GROUP BY employee, region, and that difference.
Six region islands in all — and Irene's East then West are two
islands inside her single session, so sessions and islands are
different groupings of the same rows.
"""

from __future__ import annotations

import sqlite3


def region_islands(
    conn: sqlite3.Connection,
) -> list[tuple[int, str, str, str, int, int | None]]:
    """One row per consecutive run of the same region, per employee.

    David: East Jan 5–12 (2 orders, $20,000), West Feb 20 alone
    (total NULL). Frank: West Jan 20–Feb 2 (2 orders, $20,000),
    East Mar 1 alone ($9,000). Irene: East Feb 10 alone ($25,000),
    West Feb 15 alone ($7,000). Six islands in total.
    """
    return conn.execute(
        """
        WITH numbered AS (
            SELECT employee_id, order_date, region, amount,
                   ROW_NUMBER() OVER (
                       PARTITION BY employee_id ORDER BY order_date
                   ) - ROW_NUMBER() OVER (
                       PARTITION BY employee_id, region ORDER BY order_date
                   ) AS island_id
            FROM orders
        )
        SELECT employee_id, region,
               MIN(order_date) AS island_start,
               MAX(order_date) AS island_end,
               COUNT(*) AS orders, SUM(amount) AS total
        FROM numbered
        GROUP BY employee_id, region, island_id
        ORDER BY employee_id ASC, MIN(order_date) ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("region islands:", region_islands(conn))
