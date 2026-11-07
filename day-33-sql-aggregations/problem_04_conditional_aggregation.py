"""Day 33 - Problem 4: Conditional aggregation — COUNT/SUM with a CASE
inside, plus what NULL does to your aggregates.

Two lessons in one file. First, CASE WHEN inside an aggregate lets
one query answer several questions per group: headcount, how many of
them are high earners, and what the high earners cost — no second
pass, no self-join. Second, NULLs are ignored by COUNT(column), SUM
and AVG, but not by COUNT(*): the orders table has 8 rows and only 7
amounts, because David's pending quote (order 7) has no amount yet.

Beginner foothold: COUNT(*) counts rows; COUNT(amount) counts
amounts. A row with no amount is still a row — an order that exists
but has no money attached yet. SUM(amount) quietly skips it, so the
West total is 27,000, not 27,000-plus-a-hole. If you need the hole
counted, count the difference yourself.

Two functions, one concept: high-earner stats per department (CASE
WHEN inside COUNT/SUM, COALESCE so HR's zero stays 0 instead of
NULL), and per-region order stats showing COUNT(*) vs COUNT(amount).
"""

from __future__ import annotations

import sqlite3


def high_earner_stats_by_department(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int, int]]:
    """Per department: headcount, high earners (>= 120,000), and the
    high earners' combined salary.

    Data: 2 people, 2 high earners, 280,000. Engineering: 5, 2,
    335,000. HR: 2, 0, 0 — COALESCE keeps the SUM at 0 instead of
    NULL when no row matches the CASE. Legal: 1, 1, 125,000. Sales:
    3, 1, 175,000.
    """
    return conn.execute(
        """
        SELECT
            department,
            COUNT(*),
            COUNT(CASE WHEN salary >= 120000 THEN 1 END),
            COALESCE(SUM(CASE WHEN salary >= 120000 THEN salary END), 0)
        FROM employees
        GROUP BY department
        ORDER BY department ASC
        """
    ).fetchall()


def order_stats_by_region(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int, int]]:
    """Per region: order rows, orders with an amount, total amount.

    East: 4 rows, 4 amounts, 54,000. West: 4 rows but only 3 amounts
    and 27,000 — order 7's NULL amount is skipped by COUNT(amount)
    and SUM(amount), not by COUNT(*).
    """
    return conn.execute(
        """
        SELECT region, COUNT(*), COUNT(amount), SUM(amount)
        FROM orders
        GROUP BY region
        ORDER BY region ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    for dept, headcount, high, high_total in high_earner_stats_by_department(conn):
        print(f"{dept:12} headcount={headcount} high_earners={high} high_total={high_total}")
    for region, rows, with_amount, total in order_stats_by_region(conn):
        print(f"{region}: rows={rows} with_amount={with_amount} total={total}")
