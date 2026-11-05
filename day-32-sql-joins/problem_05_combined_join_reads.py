"""Day 32 - Problem 5: combined join + filter + sort — the dashboard
reads, joining three tables and ending with ORDER BY + LIMIT.

Problems 1–4 were the join types. A real read stacks them: join the
tables, filter to the slice that matters, sort, take the top N. No
new clause appears here — JOIN + WHERE + ORDER BY + LIMIT, the
Day 31 tools plus today's joins, composed the way a stakeholder
request actually arrives.

Beginner foothold: read the query as a sentence again. "Employee
names, project names, and hours — for Engineering staff on active
projects — most hours first — just the top three." Every clause you
already know; only the FROM grew a join.

Two functions: the top-N assignment leaderboard, and the
still-unassigned engineers (LEFT JOIN + IS NULL from Problem 2,
filtered to one department and sorted).
"""

from __future__ import annotations

import sqlite3


def engineering_active_leaderboard(
    conn: sqlite3.Connection, limit: int
) -> list[tuple[str, str, int]]:
    """Top ``limit`` Engineering assignments on active projects:
    employee, project, hours — hours DESC, name ASC as tie-break."""
    return conn.execute(
        """
        SELECT e.name, p.project_name, a.hours
        FROM employees e
        JOIN assignments a ON e.id = a.employee_id
        JOIN projects p ON a.project_id = p.project_id
        WHERE e.department = 'Engineering' AND p.status = 'active'
        ORDER BY a.hours DESC, e.name ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def unassigned_engineers(conn: sqlite3.Connection) -> list[str]:
    """Engineering employees holding no assignment, alphabetically."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT e.name
            FROM employees e
            LEFT JOIN assignments a ON e.id = a.employee_id
            WHERE e.department = 'Engineering' AND a.project_id IS NULL
            ORDER BY e.name ASC
            """
        ).fetchall()
    ]


def assignments_with_location(
    conn: sqlite3.Connection, limit: int
) -> list[tuple[str, str, str, int]]:
    """Assignments enriched with the employee's department location:
    a four-table read (employees, departments, assignments, projects),
    hours DESC, capped at ``limit``."""
    return conn.execute(
        """
        SELECT e.name, p.project_name, d.location, a.hours
        FROM employees e
        JOIN departments d ON e.department = d.dept_name
        JOIN assignments a ON e.id = a.employee_id
        JOIN projects p ON a.project_id = p.project_id
        ORDER BY a.hours DESC, e.name ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("Eng active leaderboard, top 3:", engineering_active_leaderboard(conn, 3))
    print("unassigned engineers:", unassigned_engineers(conn))
    print("assignments with location, top 3:", assignments_with_location(conn, 3))
