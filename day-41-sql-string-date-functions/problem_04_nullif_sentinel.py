"""Day 41, problem 4: NULLIF the 'N/A' sentinel.

Source systems rarely send a real NULL for "no value". They send
'N/A', 'NULL', '-', or an empty string, and CAST turns every one
of them into 0 — which then counts in COUNT and drags down AVG.
Order 7's 'N/A' is not a zero-dollar order; it is David's pending
quote, the same NULL amount the clean orders table holds. NULLIF
turns a sentinel back into a real NULL: NULLIF(cleaned, 'N/A')
returns NULL when the value is 'N/A', and the value otherwise.
On the cleaned amounts, without NULLIF COUNT is 8 and AVG is
10,125 (the 0 counts); with NULLIF COUNT is 7 and AVG is
11,571.43 — the average of the seven real orders.
"""

from __future__ import annotations

import sqlite3

CLEANED = "REPLACE(REPLACE(amount_text, ',', ''), '$', '')"
CLEANED_AMOUNT = f"CAST(NULLIF({CLEANED}, 'N/A') AS INTEGER)"


def cast_na_sentinel(conn: sqlite3.Connection) -> int:
    """CAST('N/A' AS INTEGER) — 0, not NULL. That is the trap."""
    return conn.execute("SELECT CAST('N/A' AS INTEGER)").fetchone()[0]


def count_avg_no_nullif(conn: sqlite3.Connection) -> tuple[int, float]:
    """(COUNT, AVG) of cleaned CASTs without NULLIF: 8 orders, AVG 10,125."""
    return conn.execute(
        f"SELECT COUNT(CAST({CLEANED} AS INTEGER)), AVG(CAST({CLEANED} AS INTEGER)) "
        "FROM staged_raw"
    ).fetchone()


def count_avg_with_nullif(conn: sqlite3.Connection) -> tuple[int, float]:
    """(COUNT, AVG) with NULLIF: 7 real orders, AVG 11,571.43."""
    return conn.execute(
        f"SELECT COUNT({CLEANED_AMOUNT}), AVG({CLEANED_AMOUNT}) FROM staged_raw"
    ).fetchone()


def cleaned_amount_of_order(conn: sqlite3.Connection, order_id: int) -> int | None:
    """The cleaned amount of one order — order 7 ('N/A') is None, not 0."""
    return conn.execute(
        f"SELECT {CLEANED_AMOUNT} FROM staged_raw WHERE order_id = ?",
        (order_id,),
    ).fetchone()[0]
