"""Day 47, problem 2: Type 2 - close the old row, insert a new one.

Frank Lopez moves from Sales to Data on 2026-03-01, salary $98,000
-> $115,000. That is a real change, so history must survive: the old
row is closed (valid_to = 2026-03-01, is_current = 0) and a new row
opens (valid_from = 2026-03-01, is_current = 1). Frank now has 2
rows, and the dates are half-open [valid_from, valid_to): the old row
covers up to but not including 2026-03-01, the new row from it. No
gap, no overlap - an as-of query returns exactly one Frank on every
date. Close with valid_to = '2026-02-28' and Frank vanishes from
every report run for 2026-02-28.
"""

from __future__ import annotations

import sqlite3

EFFECTIVE = "2026-03-01"


def apply_type2_move(conn: sqlite3.Connection) -> None:
    """Close Frank's Sales row and open his Data row, in one transaction."""
    conn.execute(
        "UPDATE dim_employee_scd SET valid_to = ?, is_current = 0 "
        "WHERE employee_id = 7 AND is_current = 1",
        (EFFECTIVE,),
    )
    conn.execute(
        "INSERT INTO dim_employee_scd VALUES "
        "(7, 'Frank Lopez', 'Data', 'West', 115000, NULL, ?, '9999-12-31', 1)",
        (EFFECTIVE,),
    )
    conn.commit()


def frank_rows(conn: sqlite3.Connection) -> list[tuple]:
    """(department, salary, valid_from, valid_to, is_current), oldest first."""
    rows = conn.execute(
        "SELECT department, salary, valid_from, valid_to, is_current "
        "FROM dim_employee_scd WHERE employee_id = 7 ORDER BY valid_from"
    ).fetchall()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


def frank_current(conn: sqlite3.Connection) -> tuple:
    """Frank's current row: Data, $115,000, from 2026-03-01."""
    r = conn.execute(
        "SELECT department, salary, valid_from FROM dim_employee_scd "
        "WHERE employee_id = 7 AND is_current = 1"
    ).fetchone()
    return (r[0], r[1], r[2])


def frank_asof(conn: sqlite3.Connection, on: str) -> tuple:
    """Frank's department and salary as of a date (half-open interval)."""
    r = conn.execute(
        "SELECT department, salary FROM dim_employee_scd "
        "WHERE employee_id = 7 AND valid_from <= ? AND valid_to > ?",
        (on, on),
    ).fetchone()
    return (r[0], r[1])


def frank_has_overlap(conn: sqlite3.Connection) -> bool:
    """True if any two Frank rows overlap in time. After a correct
    Type 2 there is none: the old row ends exactly where the new one
    starts."""
    return (
        conn.execute(
            "SELECT COUNT(*) FROM dim_employee_scd a "
            "JOIN dim_employee_scd b ON a.employee_id = b.employee_id "
            "AND a.rowid < b.rowid "
            "AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to "
            "WHERE a.employee_id = 7"
        ).fetchone()[0]
        > 0
    )
