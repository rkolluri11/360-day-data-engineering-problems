"""Day 33 - Problem 1: GROUP BY basics — collapse rows into one row per group.

Day 31 filtered rows; Day 32 stitched tables. Aggregation collapses:
GROUP BY department turns 13 employee rows into 5 department rows,
and COUNT / SUM / AVG decide what each collapsed row says.

Beginner foothold: GROUP BY is a sorting hat. Every employee row is
dropped into a bucket labelled by its department, then the aggregate
counts or adds up each bucket. "Operations" never appears — it has no
employees, so it has no bucket. "Legal" appears with a headcount of 1:
Nina Patel is a group of one, and she still counts.

Two functions, one concept: the per-department salary summary, and
the whole-company totals (a GROUP BY with no key is a single bucket).
"""

from __future__ import annotations

import sqlite3


def department_salary_summary(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int, float]]:
    """Per department: headcount, total salary, average salary.

    Ordered by department name. Engineering: 5 people, 667,000 total,
    133,400 average. Legal: 1 person, 125,000 total, 125,000 average.
    Operations is absent — no employees, no group.
    """
    return conn.execute(
        """
        SELECT department, COUNT(*), SUM(salary), AVG(salary)
        FROM employees
        GROUP BY department
        ORDER BY department ASC
        """
    ).fetchall()


def company_totals(conn: sqlite3.Connection) -> tuple[int, int, float]:
    """Whole company: headcount, total salary, average salary.

    No GROUP BY key means one group: 13 people, 1,620,000 total,
    ~124,615.38 average.
    """
    return conn.execute(
        """
        SELECT COUNT(*), SUM(salary), AVG(salary)
        FROM employees
        """
    ).fetchone()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    for dept, headcount, total, avg in department_salary_summary(conn):
        print(f"{dept:12} headcount={headcount} total={total:>7} avg={avg:,.2f}")
    print("company totals (headcount, total, avg):", company_totals(conn))
