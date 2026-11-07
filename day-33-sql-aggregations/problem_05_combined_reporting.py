"""Day 33 - Problem 5: Combined reporting — the rollup queries a
dashboard actually runs.

Everything from Problems 1–4 in one read: join, group, aggregate,
filter groups with HAVING, order the result. The project rollup is
the weekly status report — per project, how many people, how many
hours, how heavy the average assignment — for projects with more
than 10 total hours. Delta (planning, no assignments) drops out of
the HAVING filter, which is the correct answer for a "what got done"
report and the wrong answer for a "what exists" report; know which
one you were asked for.

Beginner foothold: this is the whole day in one query. JOIN stitches
the tables, GROUP BY picks the grain (one row per project), the
aggregates fill in the numbers, HAVING keeps only the groups that
matter, ORDER BY puts the biggest first. Read it bottom-up when it
confuses you: grain first, then filters, then numbers.

Two functions, one concept: the per-project hours rollup, and the
per-region revenue summary with a HAVING threshold — at 30,000 only
the East (54,000) clears the bar.
"""

from __future__ import annotations

import sqlite3


def project_hours_rollup(
    conn: sqlite3.Connection, min_total_hours: int
) -> list[tuple[str, int, int, float]]:
    """Per project: distinct people, total hours, average hours per
    assignment — only projects above ``min_total_hours`` total hours.

    At a 10-hour bar: Apollo (3 people, 35 hours, ~11.67 avg),
    Beacon (3 people, 33 hours, 11.0 avg), Cypress (2 people,
    28 hours, 14.0 avg), ordered by total hours DESC. Delta has no
    assignments, so its total is 0 and HAVING drops it.
    """
    return conn.execute(
        """
        SELECT
            p.project_name,
            COUNT(DISTINCT a.employee_id),
            COALESCE(SUM(a.hours), 0),
            AVG(a.hours)
        FROM projects p
        LEFT JOIN assignments a ON p.project_id = a.project_id
        GROUP BY p.project_name
        HAVING COALESCE(SUM(a.hours), 0) > ?
        ORDER BY SUM(a.hours) DESC
        """,
        (min_total_hours,),
    ).fetchall()


def region_revenue_above(
    conn: sqlite3.Connection, threshold: int
) -> list[tuple[str, int, int]]:
    """Per region: order count and total revenue, only regions whose
    total revenue exceeds ``threshold``.

    At 30,000: East alone (4 orders, 54,000). West totals 27,000 and
    is filtered out as a group. The NULL-amount order never inflates
    or deflates the total — SUM skips it.
    """
    return conn.execute(
        """
        SELECT region, COUNT(*), SUM(amount)
        FROM orders
        GROUP BY region
        HAVING SUM(amount) > ?
        ORDER BY SUM(amount) DESC
        """,
        (threshold,),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    for name, people, total, avg in project_hours_rollup(conn, 10):
        print(f"{name:8} people={people} total_hours={total} avg_hours={avg:.2f}")
    print("regions above 30000 revenue:", region_revenue_above(conn, 30000))
