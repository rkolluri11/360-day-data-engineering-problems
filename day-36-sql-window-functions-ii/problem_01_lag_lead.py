"""Day 36 - Problem 1: LAG and LEAD — look back, look forward.

Day 35 numbered rows. LAG reads the previous row in the window,
LEAD reads the next one — same PARTITION BY / ORDER BY, no rows
collapsed. In Engineering, highest salary first: Alice Chen's
previous salary is Grace Liu's $190,000 (a $45,000 gap); Henry
Wong's previous is Bob Martinez's $110,000 (a $0 gap — they tie).
The first row in each window has no previous row, so LAG is NULL.
"""

from __future__ import annotations

import sqlite3


def prev_salary_in_department(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int, int | None, int | None]]:
    """Every employee with the previous salary in their department.

    Highest salary first, name ASC as the tie-breaker. Engineering:
    Grace Liu prev NULL, Alice Chen prev 190,000, Carol Davis
    prev 145,000, Bob Martinez prev 112,000, Henry Wong prev 110,000.
    """
    return conn.execute(
        """
        SELECT department, name, salary,
               LAG(salary) OVER (
                   PARTITION BY department
                   ORDER BY salary DESC, name ASC
               ) AS prev_salary,
               salary - LAG(salary) OVER (
                   PARTITION BY department
                   ORDER BY salary DESC, name ASC
               ) AS gap_vs_previous
        FROM employees
        ORDER BY department ASC, salary DESC, name ASC
        """
    ).fetchall()


def next_salary_in_department(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int, int | None]]:
    """Every employee with the next salary in their department.

    LEAD is the same look, one row ahead. Grace Liu's next salary
    is Alice Chen's $145,000; the last row in each department has
    LEAD NULL — Henry Wong's next salary is NULL.
    """
    return conn.execute(
        """
        SELECT department, name, salary,
               LEAD(salary) OVER (
                   PARTITION BY department
                   ORDER BY salary DESC, name ASC
               ) AS next_salary
        FROM employees
        ORDER BY department ASC, salary DESC, name ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("prev salary:", prev_salary_in_department(conn))
    print("next salary:", next_salary_in_department(conn))
