"""Day 35 - Problem 2: RANK vs DENSE_RANK — ties share, then what?

ROW_NUMBER never ties, so it invents an order between equals. RANK
and DENSE_RANK refuse to: tied rows share a rank. They differ in
what happens next. RANK counts people, so a tie consumes the ranks
behind it; DENSE_RANK counts distinct values, so the numbering
never skips.

Beginner foothold: a race where two runners cross the line together.
Both are 8th. Under RANK the next runner is 10th — there is no 9th,
because 9 people finished ahead of them. Under DENSE_RANK the next
runner is 9th — nine distinct finishing times came before them.

This dataset's tie: Bob Martinez and Henry Wong, both $110,000.
Company-wide both are rank 8. The next person, Mia Brown ($105,000),
is 10 under RANK and 9 under DENSE_RANK — the one-number difference
that makes a leaderboard look like someone is missing.
"""

from __future__ import annotations

import sqlite3


def rank_company(conn: sqlite3.Connection) -> list[tuple[str, int, int]]:
    """Every employee with their company-wide RANK by salary DESC.

    Bob Martinez and Henry Wong share rank 8; Mia Brown is 10.
    Ordered by rank, then name.
    """
    return conn.execute(
        """
        SELECT name, salary,
               RANK() OVER (ORDER BY salary DESC) AS r
        FROM employees
        ORDER BY r ASC, name ASC
        """
    ).fetchall()


def dense_rank_company(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int]]:
    """Every employee with their company-wide DENSE_RANK by salary DESC.

    Same tie, no gap: Bob Martinez and Henry Wong share rank 8;
    Mia Brown is 9. Ordered by rank, then name.
    """
    return conn.execute(
        """
        SELECT name, salary,
               DENSE_RANK() OVER (ORDER BY salary DESC) AS dr
        FROM employees
        ORDER BY dr ASC, name ASC
        """
    ).fetchall()


def rank_in_department(
    conn: sqlite3.Connection,
) -> list[tuple[str, str, int, int]]:
    """RANK inside each department, highest salary first.

    The Engineering tie shows up here too: Bob Martinez and Henry
    Wong are both 4th in Engineering, and there is no 5th — the next
    rank after 4 would be 6. Ordered by department, then rank.
    """
    return conn.execute(
        """
        SELECT department, name, salary,
               RANK() OVER (
                   PARTITION BY department
                   ORDER BY salary DESC
               ) AS r
        FROM employees
        ORDER BY department ASC, r ASC, name ASC
        """
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("rank company:      ", rank_company(conn))
    print("dense rank company:", dense_rank_company(conn))
    print("rank in department:", rank_in_department(conn))
