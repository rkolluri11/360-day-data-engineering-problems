"""Day 35 - Problem 3: Top-N per group — number first, filter second.

The most common window-function query in production: "top N per
group" — top 2 earners per department, top 3 orders per customer,
latest 5 events per device. The shape never changes: number the rows
inside each group, wrap the query, then filter on the number.

Beginner foothold: you cannot filter on a window function in WHERE,
because window functions run after WHERE does. So the numbering
lives in a subquery (or a CTE, Day 34's named step), and the filter
lives outside it. `WHERE rn <= 2` on the bare query is a syntax
error; the same filter one level out is the whole pattern.

Two edges, both in this dataset: Legal has one employee, so top 2
per department returns 9 people, not 10 — a group smaller than N
sends fewer rows. And RANK <= 2 would return more than 2 rows from
a group if two people tied at rank 2; here it returns the same 9,
because no tie sits at rank 2 in any department.
"""

from __future__ import annotations

import sqlite3


def top_n_per_department(
    conn: sqlite3.Connection, n: int = 2
) -> list[tuple[str, str, int, int]]:
    """Top ``n`` earners per department, via ROW_NUMBER.

    Default n = 2 returns 9 rows: 2 each from Data, Engineering, HR,
    Sales, and 1 from Legal (Nina Patel, its only employee). Ordered
    by department, then rank.
    """
    return conn.execute(
        """
        SELECT department, name, salary, rn
        FROM (
            SELECT department, name, salary,
                   ROW_NUMBER() OVER (
                       PARTITION BY department
                       ORDER BY salary DESC, name ASC
                   ) AS rn
            FROM employees
        )
        WHERE rn <= ?
        ORDER BY department ASC, rn ASC
        """,
        (n,),
    ).fetchall()


def top_n_per_department_via_rank(
    conn: sqlite3.Connection, n: int = 2
) -> list[tuple[str, str, int, int]]:
    """Top ``n`` per department, via RANK — ties at the cutoff expand.

    RANK <= 2 keeps everyone ranked 1 or 2, so a two-way tie at rank
    2 would return 3 rows from that department. On this dataset it
    returns the same 9 rows as the ROW_NUMBER version, because no
    department has a tie at rank 2. Ordered by department, then rank.
    """
    return conn.execute(
        """
        SELECT department, name, salary, r
        FROM (
            SELECT department, name, salary,
                   RANK() OVER (
                       PARTITION BY department
                       ORDER BY salary DESC
                   ) AS r
            FROM employees
        )
        WHERE r <= ?
        ORDER BY department ASC, r ASC, name ASC
        """,
        (n,),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("top 2 per dept (row_number):", top_n_per_department(conn))
    print("top 2 per dept (rank):      ", top_n_per_department_via_rank(conn))
