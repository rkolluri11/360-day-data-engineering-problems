"""Day 39, problem 3: a text filter lies.

The same 8 orders, amounts stored as TEXT. WHERE amount_text > '10000'
compares strings: '5000', '7000', '8000' and '9000' all start with a
digit bigger than '1', so 7 rows pass — including every sub-$10,000
order. CAST the amount to INTEGER first and the real 3 big orders
remain: $12,000, $15,000 and $25,000. The NULL amount passes neither
filter, exactly as in Day 38.
"""

from __future__ import annotations

import sqlite3


def text_filter_ids(conn: sqlite3.Connection) -> list[int]:
    """Order ids passing WHERE amount_text > '10000' (string compare)."""
    rows = conn.execute(
        "SELECT order_id FROM staged_orders WHERE amount_text > '10000' ORDER BY order_id"
    ).fetchall()
    return [r[0] for r in rows]


def cast_filter_ids(conn: sqlite3.Connection) -> list[int]:
    """Order ids passing WHERE CAST(amount_text AS INTEGER) > 10000."""
    rows = conn.execute(
        """SELECT order_id FROM staged_orders
           WHERE CAST(amount_text AS INTEGER) > 10000 ORDER BY order_id"""
    ).fetchall()
    return [r[0] for r in rows]


def text_filter_count(conn: sqlite3.Connection) -> int:
    return len(text_filter_ids(conn))


def cast_filter_count(conn: sqlite3.Connection) -> int:
    return len(cast_filter_ids(conn))
