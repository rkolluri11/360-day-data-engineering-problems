"""Day 41, problem 3: REPLACE then CAST — clean before you convert.

CAST does not parse a number; it reads digits from the left and
stops at the first character it does not understand, silently.
CAST('12,000' AS INTEGER) is 12 — the comma ends the number.
CAST('$25,000' AS INTEGER) is 0 — the dollar sign ends it before
it starts. So a naive SUM(CAST(amount_text AS INTEGER)) over the
staging table is $15,041, not $81,000, and nothing errors: the
wrong total looks exactly like a right one. The fix is to strip
the formatting first — REPLACE the commas and the dollar sign —
and only then CAST. The 'N/A' row still casts to 0 here; problem 4
deals with it.
"""

from __future__ import annotations

import sqlite3

# Strip the thousand separators and the currency sign before CAST.
CLEANED = "REPLACE(REPLACE(amount_text, ',', ''), '$', '')"


def cast_examples(conn: sqlite3.Connection) -> tuple[int, int]:
    """(CAST('12,000'), CAST('$25,000')) — 12 and 0, the silent truncation."""
    return conn.execute(
        "SELECT CAST('12,000' AS INTEGER), CAST('$25,000' AS INTEGER)"
    ).fetchone()


def naive_total(conn: sqlite3.Connection) -> int:
    """SUM(CAST(amount_text AS INTEGER)) with no cleaning: 15,041."""
    return conn.execute(
        "SELECT SUM(CAST(amount_text AS INTEGER)) FROM staged_raw"
    ).fetchone()[0]


def cleaned_amounts(conn: sqlite3.Connection) -> list[int | None]:
    """Each amount after REPLACE, before CAST — the strings, in order id order."""
    rows = conn.execute(
        f"SELECT {CLEANED} FROM staged_raw ORDER BY order_id"
    ).fetchall()
    return [r[0] for r in rows]


def cleaned_total(conn: sqlite3.Connection) -> int:
    """SUM of the cleaned CASTs: 81,000 — matches the clean orders table."""
    return conn.execute(
        f"SELECT SUM(CAST({CLEANED} AS INTEGER)) FROM staged_raw"
    ).fetchone()[0]
