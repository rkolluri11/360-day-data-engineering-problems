"""Day 34 - Problem 3: CTE basics — give the inner query a name.

A Common Table Expression (WITH ... AS ...) is a subquery with a
name, written before the query that uses it instead of buried inside
it. Nothing about the result changes — the same rows come back —
but a reviewer can read the steps top to bottom instead of unwinding
nested parentheses from the inside out.

Beginner foothold: a CTE is a labelled sticky note on your desk.
Instead of whispering "the average salary per department" inside a
WHERE clause where nobody can see it, you write it on a note called
dept_avg, stick it where everyone can read it, then ask your real
question against the note. Same arithmetic, half the squinting.

Two functions prove the point: above_department_average_via_cte
returns exactly the same 5 names as Problem 1's correlated scalar
subquery (Alice, Grace, Irene, Karen, Mia), and the departments
above the average budget are Engineering and Sales. If the CTE
version and the subquery version ever disagree, one of them is
wrong — that equivalence is the test.
"""

from __future__ import annotations

import sqlite3


def above_department_average_via_cte(
    conn: sqlite3.Connection,
) -> list[str]:
    """Employees earning more than their own department's average.

    CTE version of Problem 1's correlated subquery: dept_avg computes
    one average per department up front, then the outer query joins
    each employee to their department's row. Same 5 names, readable
    top to bottom: Alice Chen, Grace Liu, Irene Novak, Karen White,
    Mia Brown. Nina Patel still misses — exactly at Legal's average.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            WITH dept_avg AS (
                SELECT department, AVG(salary) AS avg_salary
                FROM employees
                GROUP BY department
            )
            SELECT e.name
            FROM employees e
            JOIN dept_avg d ON d.department = e.department
            WHERE e.salary > d.avg_salary
            ORDER BY e.name ASC
            """
        ).fetchall()
    ]


def departments_above_avg_budget_via_cte(
    conn: sqlite3.Connection,
) -> list[tuple[str, int]]:
    """Departments whose budget beats the average department budget.

    The average of the five budgets (5,000,000 / 3,000,000 /
    2,500,000 / 1,000,000 / 2,000,000) is 2,700,000, so Engineering
    and Sales clear it. Operations is included in the average even
    though it has no employees — a CTE over departments sees
    departments, not people, and that is a deliberate choice worth
    stating out loud in review.
    """
    return conn.execute(
        """
        WITH avg_budget AS (
            SELECT AVG(budget) AS avg_b FROM departments
        )
        SELECT dept_name, budget
        FROM departments, avg_budget
        WHERE budget > avg_b
        ORDER BY dept_name ASC
        """
    ).fetchall()


def above_average_orders_via_cte(
    conn: sqlite3.Connection,
) -> list[tuple[int, str, int]]:
    """Orders larger than the average order amount.

    The CTE holds the average order amount (81,000 / 7 amounts =
    ~11,571.43 — the NULL pending quote is ignored by AVG, as in
    Day 33). Orders above it: order 1 (David, East, 12,000), order 3
    (Frank, West, 15,000) and order 5 (Irene, East, 25,000). The NULL
    order never appears: NULL > anything is UNKNOWN, so it is
    filtered out, not treated as zero.
    """
    return conn.execute(
        """
        WITH avg_amount AS (
            SELECT AVG(amount) AS avg_amt FROM orders
        )
        SELECT order_id, region, amount
        FROM orders, avg_amount
        WHERE amount > avg_amt
        ORDER BY order_id ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("above dept avg (CTE): ", above_department_average_via_cte(conn))
    print("above avg budget:     ", departments_above_avg_budget_via_cte(conn))
    print("above avg orders:     ", above_average_orders_via_cte(conn))
