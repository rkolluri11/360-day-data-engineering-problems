"""Day 46, problem 1: DISTINCT vs GROUP BY — same sellers, different questions.

DISTINCT asks "which values exist?" GROUP BY asks "one row per
group — then what?" On the orders table both give the same 3
sellers (David Kim, Frank Lopez, Irene Novak), but only GROUP BY
lets you count, sum, and filter the groups with HAVING.

- COUNT(*) = 8 orders; COUNT(DISTINCT employee_id) = 3 sellers.
- Distinct (seller, region) pairs: 6. Distinct full rows: 8 —
  no two orders are fully identical.
- COUNT(DISTINCT amount) = 7: the NULL pending quote is not
  counted. SELECT DISTINCT amount returns 8 rows including NULL.
"""

from __future__ import annotations

import sqlite3


def distinct_sellers(conn: sqlite3.Connection) -> list[str]:
    """The 3 sellers, via DISTINCT."""
    rows = conn.execute(
        "SELECT DISTINCT e.name FROM employees e "
        "JOIN orders o ON o.employee_id = e.id ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def sellers_via_group_by(conn: sqlite3.Connection) -> list[str]:
    """The same 3 sellers, via GROUP BY."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "JOIN orders o ON o.employee_id = e.id "
        "GROUP BY e.name ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def order_count(conn: sqlite3.Connection) -> int:
    """8 orders in total."""
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


def distinct_seller_count(conn: sqlite3.Connection) -> int:
    """3 distinct sellers."""
    return conn.execute(
        "SELECT COUNT(DISTINCT employee_id) FROM orders"
    ).fetchone()[0]


def distinct_seller_region_pairs(conn: sqlite3.Connection) -> int:
    """6 distinct (seller, region) pairs."""
    return conn.execute(
        "SELECT COUNT(*) FROM "
        "(SELECT DISTINCT employee_id, region FROM orders)"
    ).fetchone()[0]


def distinct_full_rows(conn: sqlite3.Connection) -> int:
    """8 distinct full order rows — no two orders are identical."""
    return conn.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT employee_id, region, "
        "amount, order_date FROM orders)"
    ).fetchone()[0]


def distinct_amount_count(conn: sqlite3.Connection) -> int:
    """7 distinct amounts — COUNT(DISTINCT) ignores the NULL quote."""
    return conn.execute(
        "SELECT COUNT(DISTINCT amount) FROM orders"
    ).fetchone()[0]


def distinct_amount_rows(conn: sqlite3.Connection) -> list:
    """SELECT DISTINCT amount returns 8 rows, NULL included."""
    rows = conn.execute(
        "SELECT DISTINCT amount FROM orders ORDER BY amount"
    ).fetchall()
    return [r[0] for r in rows]
