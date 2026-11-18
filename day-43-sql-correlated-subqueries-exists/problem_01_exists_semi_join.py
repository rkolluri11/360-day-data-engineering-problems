"""Day 43, problem 1: EXISTS — the semi-join that counts people, not rows.

A JOIN answers "which pairs match?" — so joining employees to
orders returns one row per order: 8 rows for 3 sellers, because
David sold 3 times, Frank 3 times, Irene twice. COUNT(*) over
that JOIN says 8 "sellers", and DISTINCT is a patch you have to
remember. EXISTS answers a different question — "is there at
least one?" — and returns each person once, no matter how many
matching rows exist. That is a semi-join: the right table is only
checked, never joined in, so it can never fan the rows out.

Rule of thumb: when the question is "who has at least one X?",
use EXISTS, not JOIN + DISTINCT. Reach for JOIN when you need
columns from the other table; reach for EXISTS when you only
need to know it is there.
"""

from __future__ import annotations

import sqlite3


def sellers_via_join_row_count(conn: sqlite3.Connection) -> int:
    """Rows from JOIN employees to orders: 8 — David 3, Frank 3, Irene 2."""
    return conn.execute(
        "SELECT COUNT(*) FROM employees e JOIN orders o ON o.employee_id = e.id"
    ).fetchone()[0]


def orders_per_seller(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """Orders per seller, via the JOIN: David 3, Frank 3, Irene 2."""
    rows = conn.execute(
        "SELECT e.name, COUNT(*) FROM employees e "
        "JOIN orders o ON o.employee_id = e.id "
        "GROUP BY e.name ORDER BY e.name"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def sellers_via_exists(conn: sqlite3.Connection) -> list[str]:
    """People with at least one order, via EXISTS: 3 names, once each."""
    rows = conn.execute(
        "SELECT name FROM employees e "
        "WHERE EXISTS (SELECT 1 FROM orders o WHERE o.employee_id = e.id) "
        "ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def sellers_via_join_distinct(conn: sqlite3.Connection) -> list[str]:
    """Same 3 names via JOIN + DISTINCT — correct, but the DISTINCT is load-bearing."""
    rows = conn.execute(
        "SELECT DISTINCT e.name FROM employees e "
        "JOIN orders o ON o.employee_id = e.id ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def employees_without_orders(conn: sqlite3.Connection) -> list[str]:
    """People with no order at all, via NOT EXISTS: the other 10."""
    rows = conn.execute(
        "SELECT name FROM employees e "
        "WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.employee_id = e.id) "
        "ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]
