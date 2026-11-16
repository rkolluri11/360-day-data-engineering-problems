"""Day 41, problem 1: TRIM — spaces lie.

The same customer shows up as '  David Kim ', 'david kim', and
'David Kim' in the staging table, and a naive COUNT(DISTINCT
customer_raw) says there are 7 customers. There are 3. Spaces are
invisible in a report but they are real characters: LENGTH('  David
Kim ') is 12, not 9, and '  David Kim ' <> 'David Kim' in a join.
TRIM strips leading and trailing spaces; it does not fix case, and
it does not touch spaces inside the string.
"""

from __future__ import annotations

import sqlite3


def distinct_customers_raw(conn: sqlite3.Connection) -> int:
    """Distinct customers before any cleaning: 7, not 3."""
    return conn.execute(
        "SELECT COUNT(DISTINCT customer_raw) FROM staged_raw"
    ).fetchone()[0]


def distinct_customers_trimmed(conn: sqlite3.Connection) -> int:
    """Distinct customers after TRIM: 6 — spaces gone, case still splits."""
    return conn.execute(
        "SELECT COUNT(DISTINCT TRIM(customer_raw)) FROM staged_raw"
    ).fetchone()[0]


def distinct_customers_upper_trimmed(conn: sqlite3.Connection) -> int:
    """Distinct customers after UPPER(TRIM(...)): 3 — the real answer."""
    return conn.execute(
        "SELECT COUNT(DISTINCT UPPER(TRIM(customer_raw))) FROM staged_raw"
    ).fetchone()[0]


def name_lengths(conn: sqlite3.Connection, order_id: int) -> tuple[int, int]:
    """(raw length, trimmed length) of one customer's name — order 1: 12 vs 9."""
    return conn.execute(
        "SELECT LENGTH(customer_raw), LENGTH(TRIM(customer_raw)) "
        "FROM staged_raw WHERE order_id = ?",
        (order_id,),
    ).fetchone()


def trimmed_names(conn: sqlite3.Connection) -> list[str]:
    """Every customer name, trimmed, in order id order."""
    rows = conn.execute(
        "SELECT TRIM(customer_raw) FROM staged_raw ORDER BY order_id"
    ).fetchall()
    return [r[0] for r in rows]
