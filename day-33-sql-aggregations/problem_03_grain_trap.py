"""Day 33 - Problem 3: The grain trap — aggregate at the wrong grain
and your totals lie with a straight face.

This is the problem the calendar calls out: "Grain mistakes
double-count revenue." Join employees to assignments and SUM(salary)
and Alice's 145,000 is counted twice — she holds 2 assignments — and
Carol's 112,000 twice. The query runs, returns a number, and the
number is wrong by 257,000. Nothing errors. The dashboard just lies.

Beginner foothold: the grain of a query is what one row means. After
the join, one row means "one assignment", not "one employee". SUM over
assignment-grain rows adds up salaries per assignment. COUNT(*) counts
assignments (8), not people (6). The fix is to decide the grain first:
aggregate employees before joining, or count distinct people.

Three functions, one concept: the naive salary total over the join
(1,029,000 — wrong), the true total over employees alone (772,000),
and the two ways to get the true answer from the join — DISTINCT
people, or aggregate-then-join.
"""

from __future__ import annotations

import sqlite3


def naive_total_salary_via_join(conn: sqlite3.Connection) -> int:
    """SUM(salary) after joining employees to assignments.

    WRONG on purpose: Alice (2 assignments) and Carol (2 assignments)
    have their salaries counted twice. Returns 1,029,000; the true
    total for assigned employees is 772,000.
    """
    return conn.execute(
        """
        SELECT SUM(e.salary)
        FROM employees e
        JOIN assignments a ON e.id = a.employee_id
        """
    ).fetchone()[0]


def true_total_salary_assigned(conn: sqlite3.Connection) -> int:
    """SUM(salary) over the employees who hold at least one assignment.

    Aggregate at employee grain: 6 assigned people, 772,000 total.
    """
    return conn.execute(
        """
        SELECT SUM(salary)
        FROM employees
        WHERE id IN (SELECT employee_id FROM assignments)
        """
    ).fetchone()[0]


def assignment_grain_counts(conn: sqlite3.Connection) -> tuple[int, int]:
    """(rows after the join, distinct employees in the join).

    COUNT(*) sees the join grain: 8 assignment rows. COUNT(DISTINCT)
    sees the people: 6. When those two numbers differ, every SUM over
    the join is suspect.
    """
    row = conn.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT e.id)
        FROM employees e
        JOIN assignments a ON e.id = a.employee_id
        """
    ).fetchone()
    return row[0], row[1]


def true_total_salary_aggregate_first(conn: sqlite3.Connection) -> int:
    """The fix, pattern two: collapse the many-side first, then join.

    The subquery aggregates assignments to one row per employee (their
    total hours) BEFORE the join, so each employee row joins exactly
    once and each salary is added exactly once. Note the trap inside
    the fix: grouping the employees side instead would NOT help — one
    row per employee still fans out to two rows when joined to two
    assignments. Collapse the side that multiplies. Same 772,000 as
    the direct total.
    """
    return conn.execute(
        """
        SELECT SUM(e.salary)
        FROM employees e
        JOIN (
            SELECT employee_id, SUM(hours) AS total_hours
            FROM assignments
            GROUP BY employee_id
        ) a ON e.id = a.employee_id
        """
    ).fetchone()[0]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("naive SUM over join (WRONG):", naive_total_salary_via_join(conn))
    print("true SUM, assigned staff:", true_total_salary_assigned(conn))
    print("join rows vs distinct people:", assignment_grain_counts(conn))
    print("aggregate-first fix:", true_total_salary_aggregate_first(conn))
