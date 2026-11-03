"""Day 31 - Problem 5: combined precise reads — everything from Problems
1–4 in one query each, the way a dashboard actually asks.

A reporting request never arrives as "teach me WHERE". It arrives as
"give me the shortlist": a filtered, sorted, capped list of exactly
the columns the reader needs, plus the dimension list behind it.
This problem composes the block's tools without adding new ones —
explicit columns, WHERE with OR and comparisons, multi-key ORDER BY,
LIMIT, DISTINCT — and the result is the kind of read a data engineer
writes ten times a day.

Beginner foothold: read the query top to bottom as a sentence.
"Names, titles, and salaries — of employees earning at least this
much — highest paid first, names breaking ties — just the first N."
If you can read it as a sentence, you can write it as SQL.
"""

from __future__ import annotations

import sqlite3


def high_earner_shortlist(
    conn: sqlite3.Connection, min_salary: int, limit: int
) -> list[tuple[str, str, int]]:
    """Name, title, salary for earners at or above ``min_salary``,
    salary DESC then name ASC, capped at ``limit`` rows."""
    return conn.execute(
        """
        SELECT name, title, salary FROM employees
        WHERE salary >= ?
        ORDER BY salary DESC, name ASC
        LIMIT ?
        """,
        (min_salary, limit),
    ).fetchall()


def departments_with_high_earners(
    conn: sqlite3.Connection, min_salary: int
) -> list[str]:
    """Distinct departments that have at least one earner at or above
    ``min_salary``, alphabetically."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT department FROM employees
            WHERE salary >= ?
            ORDER BY department ASC
            """,
            (min_salary,),
        ).fetchall()
    ]


def cross_department_shortlist(
    conn: sqlite3.Connection, departments: tuple[str, ...], min_salary: int, limit: int
) -> list[tuple[str, str, int]]:
    """Same shortlist restricted to ``departments`` (OR across the
    list), showing WHERE + IN alongside ORDER BY + LIMIT."""
    placeholders = ", ".join("?" for _ in departments)
    return conn.execute(
        f"""
        SELECT name, department, salary FROM employees
        WHERE department IN ({placeholders}) AND salary >= ?
        ORDER BY salary DESC, name ASC
        LIMIT ?
        """,
        (*departments, min_salary, limit),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("shortlist >=120k, top 5:", high_earner_shortlist(conn, 120000, 5))
    print("departments with >=120k:", departments_with_high_earners(conn, 120000))
    print(
        "Eng/Data >=110k, top 4:",
        cross_department_shortlist(conn, ("Engineering", "Data"), 110000, 4),
    )
