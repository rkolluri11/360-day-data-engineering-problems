"""Day 39, problem 2: padded codes don't join.

HR stores employee codes zero-padded ('001', '002', …) while the other
system stores the same ids as plain text ('1', '2', …). Compared as
TEXT, '001' is not '1' — the join returns 0 rows. CAST both sides to
INTEGER and all 13 match.
"""

from __future__ import annotations

import sqlite3


def join_raw_count(conn: sqlite3.Connection) -> int:
    """Rows where the padded code equals the plain text id, as stored."""
    row = conn.execute(
        "SELECT COUNT(*) FROM employee_refs WHERE code = id_text"
    ).fetchone()
    return row[0]


def join_cast_count(conn: sqlite3.Connection) -> int:
    """Rows once both sides are CAST to INTEGER."""
    row = conn.execute(
        """SELECT COUNT(*) FROM employee_refs
           WHERE CAST(code AS INTEGER) = CAST(id_text AS INTEGER)"""
    ).fetchone()
    return row[0]


def join_to_employees_count(conn: sqlite3.Connection) -> int:
    """Employees matched by CAST-ing the padded code to their INTEGER id."""
    row = conn.execute(
        """SELECT COUNT(*) FROM employees e
           JOIN employee_refs r ON CAST(r.code AS INTEGER) = e.id"""
    ).fetchone()
    return row[0]
