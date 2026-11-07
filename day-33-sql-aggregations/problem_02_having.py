"""Day 33 - Problem 2: HAVING — filter groups after they are built.

WHERE filters rows before grouping; HAVING filters groups after
grouping. They answer different questions, and swapping them changes
the answer — the most common aggregation bug in reporting queries.

Beginner foothold: WHERE is the bouncer at the door (a row gets in or
it doesn't), HAVING is the judge after the contest (a whole group
passes or fails). "Departments whose average salary tops 120,000"
needs HAVING: the average does not exist until the group is built,
so WHERE cannot even ask the question.

Three functions, one concept: departments by average salary (HAVING),
departments by headcount (HAVING), and the WHERE-vs-HAVING contrast —
counting high earners per department, where WHERE filters rows first
and HR vanishes entirely because none of its rows clears the bar.
"""

from __future__ import annotations

import sqlite3


def departments_with_high_avg_salary(
    conn: sqlite3.Connection, threshold: float
) -> list[tuple[str, float]]:
    """Departments whose average salary exceeds ``threshold``.

    Data (140,000), Engineering (133,400), Legal (125,000) clear
    120,000; Sales (122,666.67) clears it too — check the arithmetic
    before trusting the headline number. Ordered by average DESC.
    """
    return conn.execute(
        """
        SELECT department, AVG(salary)
        FROM employees
        GROUP BY department
        HAVING AVG(salary) > ?
        ORDER BY AVG(salary) DESC
        """,
        (threshold,),
    ).fetchall()


def departments_with_min_headcount(
    conn: sqlite3.Connection, minimum: int
) -> list[tuple[str, int]]:
    """Departments with at least ``minimum`` employees.

    At minimum 3: Engineering (5) and Sales (3). Data, HR and Legal
    are filtered out as groups, not as rows.
    """
    return conn.execute(
        """
        SELECT department, COUNT(*)
        FROM employees
        GROUP BY department
        HAVING COUNT(*) >= ?
        ORDER BY department ASC
        """,
        (minimum,),
    ).fetchall()


def high_earner_counts(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """Per department, how many employees earn more than 120,000.

    WHERE runs first: only rows above 120,000 reach the grouping, so
    HR — Leo 75,000 and Mia 105,000 — produces no group at all and
    never appears. Engineering 2, Sales 1, Data 1, Legal 1.
    (Jack Thompson earns exactly 120,000: strictly greater excludes him.)
    """
    return conn.execute(
        """
        SELECT department, COUNT(*)
        FROM employees
        WHERE salary > 120000
        GROUP BY department
        ORDER BY department ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("avg salary > 120000:", departments_with_high_avg_salary(conn, 120000))
    print("headcount >= 3:", departments_with_min_headcount(conn, 3))
    print("high earners per dept:", high_earner_counts(conn))
