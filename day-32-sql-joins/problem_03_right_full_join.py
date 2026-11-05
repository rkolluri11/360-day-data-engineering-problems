"""Day 32 - Problem 3: RIGHT and FULL JOIN — the portable patterns.

Some databases offer RIGHT JOIN (keep every row on the right) and
FULL JOIN (keep every row on both sides). SQLite's support for them
is version-dependent, so production SQL uses portable equivalents
that work everywhere:

- RIGHT JOIN = swap the tables and LEFT JOIN. "Employees RIGHT JOIN
  departments" is exactly "departments LEFT JOIN employees".
- FULL JOIN = LEFT JOIN plus, via UNION ALL, the right-side rows
  that had no match. The UNION ALL half re-finds right-side orphans
  with the same LEFT JOIN + IS NULL pattern from Problem 2.

Beginner foothold: right and full joins are not new machinery — they
are the left join pointed the other way, or run twice and stacked.
If you can write a left join, you can write all of them.
"""

from __future__ import annotations

import sqlite3


def departments_with_employees_right(conn: sqlite3.Connection) -> list[tuple[str, str | None]]:
    """Every department with its employees — the RIGHT JOIN
    equivalent (departments LEFT JOIN employees). "Operations"
    appears once, with a NULL employee."""
    return conn.execute(
        """
        SELECT d.dept_name, e.name
        FROM departments d
        LEFT JOIN employees e ON e.department = d.dept_name
        ORDER BY d.dept_name ASC, e.name ASC
        """
    ).fetchall()


def full_employee_department(conn: sqlite3.Connection) -> list[tuple[str | None, str | None]]:
    """FULL JOIN equivalent: every employee (Nina with NULL
    department row) plus every department (Operations with NULL
    employee), via LEFT JOIN UNION ALL right-side orphans."""
    return conn.execute(
        """
        SELECT e.name, d.dept_name
        FROM employees e
        LEFT JOIN departments d ON e.department = d.dept_name
        UNION ALL
        SELECT e.name, d.dept_name
        FROM departments d
        LEFT JOIN employees e ON e.department = d.dept_name
        WHERE e.id IS NULL
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    right_rows = departments_with_employees_right(conn)
    print(f"right-join equivalent: {len(right_rows)} rows")
    print("Operations row:", [r for r in right_rows if r[0] == "Operations"])
    full_rows = full_employee_department(conn)
    print(f"full-join equivalent: {len(full_rows)} rows")
    print("Nina row:", [r for r in full_rows if r[0] == "Nina Patel"])
    print("Operations row:", [r for r in full_rows if r[1] == "Operations"])
