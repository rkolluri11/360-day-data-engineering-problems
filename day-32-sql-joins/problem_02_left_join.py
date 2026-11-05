"""Day 32 - Problem 2: LEFT JOIN — keep every row on the left, match or
not.

INNER JOIN drops the unmatched, which is exactly wrong when the
question is "who is missing what". LEFT JOIN keeps every row from
the left table and fills NULLs where the right table has no match.
That NULL is the signal: it marks the orphan.

Beginner foothold: left join is a class roster with a "no homework
submitted" column. Everyone stays on the list; the missing ones just
show NULL. Three orphan hunts, one pattern each:

1. Employees with no matching department (Nina, NULL location).
2. Departments with no employees ("Operations", NULL employee).
3. Employees with no assignments (LEFT JOIN + IS NULL filter — the
   classic "find what's missing" query, combining Day 31's IS NULL
   with today's join).
"""

from __future__ import annotations

import sqlite3


def all_employees_with_location(conn: sqlite3.Connection) -> list[tuple[str, str, str | None]]:
    """Every employee; location is NULL when the department has no row."""
    return conn.execute(
        """
        SELECT e.name, e.department, d.location
        FROM employees e
        LEFT JOIN departments d ON e.department = d.dept_name
        ORDER BY e.name ASC
        """
    ).fetchall()


def departments_without_employees(conn: sqlite3.Connection) -> list[str]:
    """Departments with no employees: LEFT JOIN, then keep only the
    rows where the right side came back NULL."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT d.dept_name
            FROM departments d
            LEFT JOIN employees e ON e.department = d.dept_name
            WHERE e.id IS NULL
            ORDER BY d.dept_name ASC
            """
        ).fetchall()
    ]


def employees_without_assignments(conn: sqlite3.Connection) -> list[str]:
    """Employees holding no assignment, alphabetically."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT e.name
            FROM employees e
            LEFT JOIN assignments a ON e.id = a.employee_id
            WHERE a.project_id IS NULL
            ORDER BY e.name ASC
            """
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    rows = all_employees_with_location(conn)
    print(f"all employees: {len(rows)} rows")
    print("Nina's row:", [r for r in rows if r[0] == "Nina Patel"])
    print("departments without employees:", departments_without_employees(conn))
    print("employees without assignments:", employees_without_assignments(conn))
