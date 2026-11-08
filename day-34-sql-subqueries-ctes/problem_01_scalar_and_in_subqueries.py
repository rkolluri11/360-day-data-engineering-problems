"""Day 34 - Problem 1: Scalar and IN subqueries — a question inside a question.

Day 33 collapsed rows. A subquery does the opposite job: it computes
one value (or one list) that the outer query needs before it can
decide. A scalar subquery returns a single value — "the average
salary" — and an IN subquery returns a list — "the departments with
a big budget".

Beginner foothold: think of a subquery as asking a colleague a quick
question mid-sentence. "Who earns more than [the average salary in
their department]?" You cannot answer until the bracketed part is
answered first — and for the correlated version, the bracketed part
is re-asked once per employee, because "their department" changes
each row.

Three functions, one idea: above-department-average (correlated
scalar), above-company-average (plain scalar), and employees in
big-budget departments (IN list). The first and second lists differ
by exactly one person — Mia vs Nina — which is the whole lesson:
"above average" means nothing until you say *average of what*.
"""

from __future__ import annotations

import sqlite3


def above_department_average(
    conn: sqlite3.Connection,
) -> list[str]:
    """Employees earning more than their own department's average.

    Correlated scalar subquery: the inner AVG is re-evaluated for
    each employee's department. Alice Chen, Grace Liu, Irene Novak,
    Karen White, Mia Brown — 5 people. Nina Patel earns exactly her
    department's average (125,000, Legal's only salary), so she is
    NOT above it.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees e
            WHERE salary > (
                SELECT AVG(salary) FROM employees
                WHERE department = e.department
            )
            ORDER BY name ASC
            """
        ).fetchall()
    ]


def above_company_average(conn: sqlite3.Connection) -> list[str]:
    """Employees earning more than the whole-company average.

    Plain scalar subquery: one value (124,615.38) computed once.
    Alice Chen, Grace Liu, Irene Novak, Karen White, Nina Patel —
    5 people. Compare with above_department_average: Nina swaps in
    for Mia. Same question shape, different denominator, different
    answer — which is why "above average" without a denominator is
    a bug report waiting to happen.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees
            WHERE salary > (SELECT AVG(salary) FROM employees)
            ORDER BY name ASC
            """
        ).fetchall()
    ]


def in_big_budget_departments(
    conn: sqlite3.Connection, min_budget: int = 3000000
) -> list[str]:
    """Employees whose department's budget clears ``min_budget``.

    IN subquery: the inner query returns a list of department names
    (Engineering 5,000,000 and Sales 3,000,000 at the default
    threshold), and the outer query keeps employees in that list.
    8 people: all 5 in Engineering, all 3 in Sales. Operations has
    a 2,000,000 budget and no employees, so it never appears either
    way — IN can only return people who exist.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees
            WHERE department IN (
                SELECT dept_name FROM departments WHERE budget >= ?
            )
            ORDER BY name ASC
            """,
            (min_budget,),
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("above dept avg:     ", above_department_average(conn))
    print("above company avg:  ", above_company_average(conn))
    print("big-budget depts:   ", in_big_budget_departments(conn))
