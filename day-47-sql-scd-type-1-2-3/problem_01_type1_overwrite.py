"""Day 47, problem 1: Type 1 - overwrite, no history kept.

David Kim's salary was recorded as $95,000. Payroll says it was a
data-entry error: the correct figure is $96,000, and it was $96,000
all along. That is a correction, not a change - so Type 1 overwrites
the value in place. One row before, one row after, and the old value
is gone: a report re-run for February now says David earned $96,000,
even though he was paid $95,000. Type 1 rewrites history. Use it
only for fixes, never for real changes.
"""

from __future__ import annotations

import sqlite3

CORRECTED_SALARY = 96000


def apply_type1_correction(conn: sqlite3.Connection) -> None:
    """Overwrite David's salary in place. No new row, no dates touched."""
    conn.execute(
        "UPDATE dim_employee_scd SET salary = ? "
        "WHERE employee_id = 6 AND is_current = 1",
        (CORRECTED_SALARY,),
    )
    conn.commit()


def david_salary(conn: sqlite3.Connection) -> int:
    """David's (single) salary after the correction."""
    return conn.execute(
        "SELECT salary FROM dim_employee_scd WHERE employee_id = 6"
    ).fetchone()[0]


def david_row_count(conn: sqlite3.Connection) -> int:
    """Type 1 adds no rows: David still has exactly 1 row."""
    return conn.execute(
        "SELECT COUNT(*) FROM dim_employee_scd WHERE employee_id = 6"
    ).fetchone()[0]


def old_salary_survives(conn: sqlite3.Connection) -> bool:
    """False: no row anywhere still holds the old $95,000."""
    return (
        conn.execute(
            "SELECT COUNT(*) FROM dim_employee_scd "
            "WHERE employee_id = 6 AND salary = 95000"
        ).fetchone()[0]
        > 0
    )


def david_valid_from(conn: sqlite3.Connection) -> str:
    """Type 1 does not touch the dates: still valid from 2026-01-01."""
    return conn.execute(
        "SELECT valid_from FROM dim_employee_scd WHERE employee_id = 6"
    ).fetchone()[0]
