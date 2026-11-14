"""Day 39, problem 5: a cast on a column kills the index.

salary has an index. WHERE salary = 110000 SEARCHes it. Wrap the
column in CAST and the planner can no longer use the index — the same
query SCANs every row. Fix the data, or cast the constant, never the
column you search.

Same lesson, second half: division follows the type too. SUM(amount) /
COUNT(amount) is integer division — 11,571, the cents dropped. AVG
returns the real 11,571.43.
"""

from __future__ import annotations

import sqlite3


def plan_uses_index(conn: sqlite3.Connection, sql: str) -> bool:
    """True when EXPLAIN QUERY PLAN shows an index SEARCH for the query."""
    rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
    return any("SEARCH" in r[3] and "INDEX" in r[3] for r in rows)


def plain_salary_uses_index(conn: sqlite3.Connection) -> bool:
    return plan_uses_index(
        conn, "SELECT * FROM employees WHERE salary = 110000"
    )


def cast_salary_uses_index(conn: sqlite3.Connection) -> bool:
    return plan_uses_index(
        conn, "SELECT * FROM employees WHERE CAST(salary AS TEXT) = '110000'"
    )


def int_division_average(conn: sqlite3.Connection) -> int:
    """SUM(amount) / COUNT(amount) over the priced orders — truncated."""
    row = conn.execute(
        "SELECT SUM(amount) / COUNT(amount) FROM orders WHERE amount IS NOT NULL"
    ).fetchone()
    return row[0]


def real_average(conn: sqlite3.Connection) -> float:
    """AVG(amount) over the priced orders — the real average."""
    row = conn.execute(
        "SELECT AVG(amount) FROM orders WHERE amount IS NOT NULL"
    ).fetchone()
    return row[0]
