"""Day 31 - Problem 3: ORDER BY + LIMIT — sorting and top-N.

Problem 1's note was a warning: without ORDER BY, row order is an
accident of storage, not a promise. ORDER BY makes order part of the
query's contract. DESC puts the biggest first; ASC the smallest.
LIMIT then takes the top N — but LIMIT without ORDER BY takes an
arbitrary N, which is how "top 5 customers" reports silently lie.

Beginner foothold: ORDER BY is the sort button on a spreadsheet,
LIMIT is "show me only the first N rows". The tie-break rule matters:
two employees share salary 110000, so a second key (name ASC) makes
their order deterministic instead of storage-dependent.

Two functions: top earners overall, and the lowest earners (ASC).
"""

from __future__ import annotations

import sqlite3


def top_earners(conn: sqlite3.Connection, n: int) -> list[tuple[str, int]]:
    """Top ``n`` earners: salary DESC, name ASC as tie-break."""
    return conn.execute(
        """
        SELECT name, salary FROM employees
        ORDER BY salary DESC, name ASC
        LIMIT ?
        """,
        (n,),
    ).fetchall()


def lowest_earners(conn: sqlite3.Connection, n: int) -> list[tuple[str, int]]:
    """Bottom ``n`` earners: salary ASC, name ASC as tie-break."""
    return conn.execute(
        """
        SELECT name, salary FROM employees
        ORDER BY salary ASC, name ASC
        LIMIT ?
        """,
        (n,),
    ).fetchall()


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("top 5:", top_earners(conn, 5))
    print("bottom 3:", lowest_earners(conn, 3))
    print("all, limit 100:", len(top_earners(conn, 100)), "rows")
