"""Day 31 - Problem 2: WHERE filtering — AND, comparisons, and LIKE.

SELECT reads; WHERE decides which rows deserve to be read. Almost
every real query is a filter, and most filter bugs are logic bugs:
AND narrows (both conditions must hold), OR widens (either holds),
and forgetting which one you meant returns the wrong headcount.

Beginner foothold: WHERE is a bouncer with a checklist. Each row
walks up, the condition is checked, and only rows passing every
ANDed condition get in. LIKE adds pattern matching: ``%`` means "any
characters, including none", so ``'C%'`` matches every name starting
with C.

Two functions, one concept: exact-match + comparison filtering, and
prefix pattern matching.
"""

from __future__ import annotations

import sqlite3


def by_department_and_salary(
    conn: sqlite3.Connection, department: str, min_salary: int
) -> list[tuple[str, int]]:
    """Names and salaries in ``department`` earning strictly above
    ``min_salary``. Both conditions must hold (AND)."""
    return conn.execute(
        """
        SELECT name, salary FROM employees
        WHERE department = ? AND salary > ?
        """,
        (department, min_salary),
    ).fetchall()


def by_name_prefix(conn: sqlite3.Connection, prefix: str) -> list[str]:
    """Names starting with ``prefix`` (LIKE pattern, case-insensitive
    for ASCII in SQLite)."""
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM employees WHERE name LIKE ?",
            (prefix + "%",),
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("Eng above 110k:", by_department_and_salary(conn, "Engineering", 110000))
    print("Names starting with C:", by_name_prefix(conn, "C"))
    print("Names starting with Z:", by_name_prefix(conn, "Z"))
