"""Day 41, problem 5: date normalization — three formats, one column.

The staging dates arrive in three formats: ISO ('2026-01-05'),
US ('01/12/2026'), and month-name ('Jan 20, 2026'). SQLite's
DATE() only understands ISO, so it parses 3 of 8 and returns NULL
for the other 5 — and a NULL date silently drops the row from a
monthly GROUP BY. The fix is a CASE that rebuilds each format
into ISO: SUBSTR slices the US format into year-month-day, and a
month-name CASE maps 'Jan'/'Feb'/'Mar' to '01'/'02'/'03'. Once
normalized, all 8 dates land exactly on the clean order dates:
Jan 3 orders $35,000, Feb 4 orders $37,000, Mar 1 order $9,000,
and the julianday span from first to last order is 55 days.
"""

from __future__ import annotations

import sqlite3

# Rebuild every format into ISO 'YYYY-MM-DD'.
CLEANED_DATE = """CASE
    WHEN date_text LIKE '____-__-__' THEN DATE(date_text)
    WHEN date_text LIKE '__/__/____' THEN
        SUBSTR(date_text, 7, 4) || '-' || SUBSTR(date_text, 1, 2) || '-' || SUBSTR(date_text, 4, 2)
    ELSE
        SUBSTR(date_text, 9, 4) || '-' || CASE SUBSTR(date_text, 1, 3)
            WHEN 'Jan' THEN '01' WHEN 'Feb' THEN '02' WHEN 'Mar' THEN '03' END
        || '-' || SUBSTR(date_text, 5, 2)
END"""

CLEANED_AMOUNT = (
    "CAST(NULLIF(REPLACE(REPLACE(amount_text, ',', ''), '$', ''), 'N/A') AS INTEGER)"
)


def directly_parseable(conn: sqlite3.Connection) -> int:
    """Rows DATE(date_text) parses on its own: 3 of 8 (the ISO ones)."""
    return conn.execute(
        "SELECT COUNT(*) FROM staged_raw WHERE DATE(date_text) IS NOT NULL"
    ).fetchone()[0]


def cleaned_dates(conn: sqlite3.Connection) -> list[str]:
    """Every date normalized to ISO, in order id order."""
    rows = conn.execute(
        f"SELECT {CLEANED_DATE} FROM staged_raw ORDER BY order_id"
    ).fetchall()
    return [r[0] for r in rows]


def monthly_totals(conn: sqlite3.Connection) -> dict[str, tuple[int, int]]:
    """(order count, cleaned total) per month: Jan (3, 35000), Feb (4, 37000), Mar (1, 9000)."""
    rows = conn.execute(
        f"SELECT strftime('%Y-%m', {CLEANED_DATE}), COUNT(*), SUM({CLEANED_AMOUNT}) "
        f"FROM staged_raw GROUP BY strftime('%Y-%m', {CLEANED_DATE}) ORDER BY 1"
    ).fetchall()
    return {month: (count, total) for month, count, total in rows}


def date_span_days(conn: sqlite3.Connection) -> float:
    """Days from the first cleaned order date to the last: 55."""
    return conn.execute(
        f"SELECT julianday(MAX({CLEANED_DATE})) - julianday(MIN({CLEANED_DATE})) "
        "FROM staged_raw"
    ).fetchone()[0]
