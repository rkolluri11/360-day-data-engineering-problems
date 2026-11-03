"""Day 31 - Problem 4: NULL and DISTINCT — the two quiet data-quality
traps.

NULL is not zero, not empty string, not "unknown yet" — it is the
absence of a value, and it refuses to compare. ``manager_id = NULL``
is never true, not even for the NULL rows themselves, so it returns
nothing; ``IS NULL`` is the only test that finds them. Aggregates
agree: COUNT(manager_id) counts only non-NULL rows, while COUNT(*)
counts every row.

DISTINCT is the dedup keyword: it collapses repeated values into one
row each. Combined with ORDER BY it gives clean dimension lists —
the departments, the titles — without a GROUP BY (which arrives in
a later block).

Beginner foothold: NULL means "no answer recorded". You cannot ask
"is no answer equal to no answer" with ``=``; you ask "is there no
answer" with ``IS NULL``.
"""

from __future__ import annotations

import sqlite3


def employees_without_manager(conn: sqlite3.Connection) -> list[str]:
    """Department heads: manager_id IS NULL (never = NULL)."""
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM employees WHERE manager_id IS NULL"
        ).fetchall()
    ]


def employees_with_broken_null_test(conn: sqlite3.Connection) -> list[str]:
    """The classic bug, shown deliberately: ``= NULL`` matches nothing,
    not even the NULL rows. Always returns []."""
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM employees WHERE manager_id = NULL"
        ).fetchall()
    ]


def distinct_departments(conn: sqlite3.Connection) -> list[str]:
    """Every department, once each, alphabetically."""
    return [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT department FROM employees ORDER BY department ASC"
        ).fetchall()
    ]


def distinct_titles_in_department(conn: sqlite3.Connection, department: str) -> list[str]:
    """Distinct job titles inside one department, alphabetically."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT title FROM employees
            WHERE department = ?
            ORDER BY title ASC
            """,
            (department,),
        ).fetchall()
    ]


def manager_counts(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """(total rows, non-NULL manager_ids, distinct manager_ids).

    COUNT(*) counts rows; COUNT(manager_id) skips NULLs;
    COUNT(DISTINCT manager_id) skips NULLs and dedupes.
    """
    row = conn.execute(
        """
        SELECT COUNT(*), COUNT(manager_id), COUNT(DISTINCT manager_id)
        FROM employees
        """
    ).fetchone()
    return row[0], row[1], row[2]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("without manager:", employees_without_manager(conn))
    print("broken = NULL test:", employees_with_broken_null_test(conn))
    print("departments:", distinct_departments(conn))
    print("Eng titles:", distinct_titles_in_department(conn, "Engineering"))
    print("counts (rows, non-null mgr, distinct mgr):", manager_counts(conn))
