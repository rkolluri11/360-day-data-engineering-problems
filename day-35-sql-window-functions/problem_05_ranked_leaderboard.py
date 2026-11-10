"""Day 35 - Problem 5: The ranked leaderboard — all three functions,
one query each, plus the highest order per employee.

The capstone combines the day: rank departments by total salary
(a window function over a GROUP BY — the window runs after the
aggregation), rank every employee twice at once (inside their
department and company-wide), and pick each employee's highest
order with an explicit NULLS LAST.

Beginner foothold: a window function can sit on top of aggregated
rows. GROUP BY collapses employees into 5 department totals first;
then RANK numbers those 5 totals. The two steps compose because
they run in order: WHERE, then GROUP BY, then the window, then
ORDER BY. That order is also why the WHERE filter could not see
rn in Problem 3.

The NULLS LAST edge: David Kim's orders are $12,000, $8,000, and a
NULL pending quote. ORDER BY amount DESC with an explicit NULLS LAST
picks $12,000 as his highest order. SQLite already sorts NULL last
on DESC, but other engines put NULL first on DESC — writing NULLS
LAST makes the intent portable instead of engine-dependent.
"""

from __future__ import annotations

import sqlite3


def department_salary_leaderboard(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int]]:
    """Departments by total salary, ranked.

    Engineering 667,000 (rank 1), Sales 368,000 (2), Data 280,000
    (3), HR 180,000 (4), Legal 125,000 (5). No ties, so RANK and
    DENSE_RANK agree here.
    """
    return conn.execute(
        """
        SELECT department, total_salary, r
        FROM (
            SELECT department, SUM(salary) AS total_salary,
                   RANK() OVER (ORDER BY SUM(salary) DESC) AS r
            FROM employees
            GROUP BY department
        )
        ORDER BY r ASC
        """
    ).fetchall()


def employee_leaderboard(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int, int, int, int]]:
    """Every employee with their department rank and company ranks.

    Returns (department, name, salary, dept_rank, company_rank,
    company_dense_rank). The tie shows in all three columns at once:
    Bob Martinez and Henry Wong are both dept rank 4 in Engineering,
    company rank 8, dense rank 8 — while Mia Brown is company rank
    10 but dense rank 9. Ordered by department, then dept rank.
    """
    return conn.execute(
        """
        SELECT department, name, salary,
               RANK() OVER (
                   PARTITION BY department ORDER BY salary DESC
               ) AS dept_rank,
               RANK() OVER (ORDER BY salary DESC) AS co_rank,
               DENSE_RANK() OVER (ORDER BY salary DESC) AS co_dense
        FROM employees
        ORDER BY department ASC, dept_rank ASC, name ASC
        """
    ).fetchall()


def highest_order_per_employee(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int]]:
    """Each employee's highest-value order, NULLS LAST.

    David Kim: order 1, $12,000. Frank Lopez: order 3, $15,000.
    Irene Novak: order 5, $25,000. David's NULL pending quote never
    wins, because NULLS LAST is explicit. Ordered by employee name.
    """
    return conn.execute(
        """
        SELECT name, order_id, amount
        FROM (
            SELECT e.name, o.order_id, o.amount,
                   ROW_NUMBER() OVER (
                       PARTITION BY o.employee_id
                       ORDER BY o.amount DESC NULLS LAST
                   ) AS rn
            FROM orders o
            JOIN employees e ON e.id = o.employee_id
        )
        WHERE rn = 1
        ORDER BY name ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("dept leaderboard: ", department_salary_leaderboard(conn))
    print("employee board:   ", employee_leaderboard(conn))
    print("highest order:    ", highest_order_per_employee(conn))
