"""Day 34 - Problem 4: Chained CTEs — a pipeline written as named steps.

One CTE is a sticky note. Chained CTEs are a pipeline: each step
names its output, and the next step reads the previous note instead
of re-deriving it. This is how a 200-line nested monster becomes
five lines a reviewer can check one at a time — and how a wrong
number gets traced to exactly one step.

Beginner foothold: think of making a report in a spreadsheet. First
you add a column (hours per assignment), then a summary table
(hours per project), then you filter that table (above-average
projects). Each tab is a CTE; each tab can be eyeballed on its own.
A nested subquery is the same arithmetic with all three tabs crammed
into one cell.

Project hours: Apollo 35h, Beacon 33h, Cypress 28h (Delta has no
assignments and never enters the chain). Their average is 32h, so
Apollo and Beacon clear it. Regional revenue: East 54,000, West
27,000, average 40,500 — East alone clears it. Both chains end in
the same shape: a named step, then a filter against that step's own
average.
"""

from __future__ import annotations

import sqlite3


def project_hours_by_project(
    conn: sqlite3.Connection,
) -> list[tuple[str, int]]:
    """Total hours per project, via a two-step CTE chain.

    Step 1 (project_hours): sum hours per project_id. Step 2 joins
    the names on. Apollo 35, Beacon 33, Cypress 28 — ordered by
    project name. Delta is absent: no assignments means no row in
    step 1, and the chain never invents one.
    """
    return conn.execute(
        """
        WITH project_hours AS (
            SELECT project_id, SUM(hours) AS total_hours
            FROM assignments
            GROUP BY project_id
        )
        SELECT p.project_name, ph.total_hours
        FROM project_hours ph
        JOIN projects p ON p.project_id = ph.project_id
        ORDER BY p.project_name ASC
        """
    ).fetchall()


def above_average_projects(
    conn: sqlite3.Connection,
) -> list[tuple[str, int]]:
    """Projects with above-average total hours, via a three-step chain.

    project_hours -> project_totals (names attached) -> filter
    against the average of the totals (32h). Apollo 35h and Beacon
    33h clear it; Cypress 28h does not. The average is computed from
    the CTE itself, so adding a project later moves the bar
    automatically — the query never hard-codes 32.
    """
    return conn.execute(
        """
        WITH project_hours AS (
            SELECT project_id, SUM(hours) AS total_hours
            FROM assignments
            GROUP BY project_id
        ),
        project_totals AS (
            SELECT p.project_name, ph.total_hours
            FROM project_hours ph
            JOIN projects p ON p.project_id = ph.project_id
        )
        SELECT project_name, total_hours
        FROM project_totals
        WHERE total_hours > (SELECT AVG(total_hours) FROM project_totals)
        ORDER BY total_hours DESC
        """
    ).fetchall()


def above_average_regions(
    conn: sqlite3.Connection,
) -> list[tuple[str, int]]:
    """Regions whose order revenue beats the average region revenue.

    region_revenue -> filter against its own average. East 54,000
    and West 27,000 average 40,500, so East alone clears it. The
    NULL pending quote contributes nothing to West's 27,000 — SUM
    ignores NULLs, exactly as Day 33 showed.
    """
    return conn.execute(
        """
        WITH region_revenue AS (
            SELECT region, SUM(amount) AS revenue
            FROM orders
            GROUP BY region
        )
        SELECT region, revenue
        FROM region_revenue
        WHERE revenue > (SELECT AVG(revenue) FROM region_revenue)
        ORDER BY revenue DESC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("project hours:       ", project_hours_by_project(conn))
    print("above-avg projects:  ", above_average_projects(conn))
    print("above-avg regions:   ", above_average_regions(conn))
