"""Day 31 - Problem 1: explicit columns — ask for what you need, nothing
more.

``SELECT *`` is the beginner's default and the production incident
waiting to happen: a new column added to the table silently changes
every downstream consumer, and wide rows waste network and memory.
The discipline is to name exactly the columns you need, in the order
you need them.

Beginner foothold: a SELECT list is a shopping list. ``SELECT name,
department, salary`` returns exactly three values per row, in exactly
that order — no id, no hire date, no surprises. Aliases (``AS``) let
you rename a column for the reader without touching the table.

Note: without ORDER BY, SQLite returns rows in insertion (rowid)
order for this freshly seeded table. That order is convenient here
but is NOT a guarantee — Problem 3 teaches the clause that makes
order explicit.
"""

from __future__ import annotations

import sqlite3


def roster(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Every employee's name, department, and salary — nothing else."""
    return conn.execute(
        "SELECT name, department, salary FROM employees"
    ).fetchall()


def directory(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Name and title, with reader-friendly aliases (same values)."""
    return conn.execute(
        "SELECT name AS employee_name, title AS job_title FROM employees"
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("roster (first 3):", roster(conn)[:3])
    print("directory (first 3):", directory(conn)[:3])
    print("columns per roster row:", len(roster(conn)[0]))
