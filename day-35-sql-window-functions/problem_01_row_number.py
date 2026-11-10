"""Day 35 - Problem 1: ROW_NUMBER — a number per row, never a tie.

Day 34 nested queries. A window function does a different job: it
computes a value across a set of rows and keeps every row. GROUP BY
collapses 13 employees into 5 department rows; ROW_NUMBER keeps all
13 and numbers them. PARTITION BY restarts the numbering in each
group; ORDER BY decides the order inside it.

Beginner foothold: think of numbering seats in a theatre by section.
Every seat keeps its row, each section restarts at 1, and the order
you number in is the order people sat down.

The trap, built into this dataset on purpose: Bob Martinez and Henry
Wong both earn $110,000 in Engineering. ROW_NUMBER cannot tie, so
without a tie-breaker it picks one of them for 4 and the other for 5
— arbitrarily. The code below orders by salary DESC, name ASC, so Bob
is 4 and Henry is 5 deterministically, and the docstring says so.
"""

from __future__ import annotations

import sqlite3


def rank_in_department(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int, int]]:
    """Every employee with their ROW_NUMBER inside their department.

    Highest salary first, name ASC as the tie-breaker. Engineering:
    Grace Liu 1, Alice Chen 2, Carol Davis 3, Bob Martinez 4,
    Henry Wong 5. Ordered by department, then rank.
    """
    return conn.execute(
        """
        SELECT department, name, salary,
               ROW_NUMBER() OVER (
                   PARTITION BY department
                   ORDER BY salary DESC, name ASC
               ) AS rn
        FROM employees
        ORDER BY department ASC, rn ASC
        """
    ).fetchall()


def top_earner_per_department(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int]]:
    """The rn = 1 row per department — the top earner in each.

    Window functions run after WHERE, so the numbering must be wrapped
    in a subquery before filtering. Five rows: Grace Liu (Engineering,
    190,000), Irene Novak (Sales, 175,000), Karen White (Data,
    160,000), Nina Patel (Legal, 125,000), Mia Brown (HR, 105,000).
    """
    return conn.execute(
        """
        SELECT department, name, salary
        FROM (
            SELECT department, name, salary,
                   ROW_NUMBER() OVER (
                       PARTITION BY department
                       ORDER BY salary DESC, name ASC
                   ) AS rn
            FROM employees
        )
        WHERE rn = 1
        ORDER BY salary DESC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("rank in department:", rank_in_department(conn))
    print("top earner per dept:", top_earner_per_department(conn))
