"""Day 39, problem 4: CAST is silent.

CAST never errors on dirty text — it stops, truncates, or invents a
zero and carries on. '12,500' stops at the comma and becomes 12;
'12.9' truncates to 12; 'abc' and '' both become 0. Add the five
CASTs and you get 12,024 — a number that was never in the data.
CAST to REAL keeps the decimal: '12.9' is 12.9, not 12.
"""

from __future__ import annotations

import sqlite3


def cast_values(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """Each raw string next to CAST(raw_text AS INTEGER)."""
    return conn.execute(
        "SELECT raw_text, CAST(raw_text AS INTEGER) FROM raw_amounts"
    ).fetchall()


def cast_sum(conn: sqlite3.Connection) -> int:
    """SUM of the INTEGER casts — the silently wrong total."""
    row = conn.execute(
        "SELECT SUM(CAST(raw_text AS INTEGER)) FROM raw_amounts"
    ).fetchone()
    return row[0]


def cast_real_value(conn: sqlite3.Connection, raw: str) -> float:
    """CAST a raw string to REAL, which keeps the decimal part."""
    row = conn.execute(
        "SELECT CAST(? AS REAL)", (raw,)
    ).fetchone()
    return row[0]
