"""Day 47, problem 3: Type 3 - keep one previous value in a column.

Irene Novak's region changes East -> West on 2026-03-01. Type 3
stores the previous value in the same row: region becomes West and
previous_region becomes East. Still 1 row, dates untouched. The
price: only ONE step back exists. If Irene moves again, East is
overwritten and lost - and an as-of query for February returns West,
because the single row's region is now West. Type 3 answers "where
was she before this move?" and nothing earlier.
"""

from __future__ import annotations

import sqlite3


def apply_type3_region_change(conn: sqlite3.Connection) -> None:
    """Move Irene's region, keeping the old region in previous_region."""
    conn.execute(
        "UPDATE dim_employee_scd "
        "SET previous_region = region, region = 'West' "
        "WHERE employee_id = 8 AND is_current = 1"
    )
    conn.commit()


def irene_row(conn: sqlite3.Connection) -> tuple:
    """(region, previous_region, salary, valid_from) - one row, dates kept."""
    r = conn.execute(
        "SELECT region, previous_region, salary, valid_from "
        "FROM dim_employee_scd WHERE employee_id = 8"
    ).fetchone()
    return (r[0], r[1], r[2], r[3])


def irene_row_count(conn: sqlite3.Connection) -> int:
    """Type 3 adds no rows: Irene still has exactly 1 row."""
    return conn.execute(
        "SELECT COUNT(*) FROM dim_employee_scd WHERE employee_id = 8"
    ).fetchone()[0]


def irene_region_asof(conn: sqlite3.Connection, on: str) -> str:
    """Irene's region as the as-of query sees it. After the Type 3
    change this is West even for February dates - the as-of query
    cannot recover East as the current region; only previous_region
    remembers it. That is the Type 3 limit, stated plainly."""
    r = conn.execute(
        "SELECT region FROM dim_employee_scd "
        "WHERE employee_id = 8 AND valid_from <= ? AND valid_to > ?",
        (on, on),
    ).fetchone()
    return r[0]
