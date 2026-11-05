"""Day 32 - Problem 1: INNER JOIN — only rows that match on both sides.

Day 31 read one table. Real data lives across tables, and INNER JOIN
is the stitch: for each employee, find the department row with the
same name, and glue them together. Rows with no match on either side
are dropped, silently.

Beginner foothold: an inner join is a dance floor that only admits
pairs. An employee whose department has no row (Nina Patel, "Legal")
gets no partner and does not appear. A department with no employees
("Operations") likewise never appears — there is no employee row to
pair it with.

Two functions, one concept: employees enriched with their location,
and departments that actually have employees.
"""

from __future__ import annotations

import sqlite3


def employees_with_location(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Name, department, location for employees whose department
    exists in departments. Nina Patel ("Legal") is dropped."""
    return conn.execute(
        """
        SELECT e.name, e.department, d.location
        FROM employees e
        INNER JOIN departments d ON e.department = d.dept_name
        ORDER BY e.name ASC
        """
    ).fetchall()


def departments_with_employees(conn: sqlite3.Connection) -> list[str]:
    """Departments that have at least one employee. "Operations"
    (no employees) is dropped."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT d.dept_name
            FROM departments d
            INNER JOIN employees e ON e.department = d.dept_name
            ORDER BY d.dept_name ASC
            """
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    rows = employees_with_location(conn)
    print(f"employees with location: {len(rows)} rows (Nina dropped)")
    print("first 3:", rows[:3])
    print("departments with employees:", departments_with_employees(conn))
