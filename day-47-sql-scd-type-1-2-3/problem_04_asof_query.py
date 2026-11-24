"""Day 47, problem 4: the as-of query and the current view.

With all three changes applied, the dimension holds 4 rows for 3
people. Two ways to read it:

- Current view: WHERE is_current = 1 gives 3 rows - David $96,000
  Sales, Frank $115,000 Data, Irene $175,000 Sales/West.
- As-of a date: valid_from <= date AND valid_to > date (half-open)
  gives exactly one row per person on every date. On 2026-02-15
  Frank is Sales at $98,000; on 2026-03-15 he is Data at $115,000.
  The same query also exposes what the types cost: David shows
  $96,000 even in February (Type 1 rewrote history - he was paid
  $95,000), and Irene shows region West even in February (Type 3
  overwrote it - she was East; only previous_region knows).
"""

from __future__ import annotations

import sqlite3

from problem_01_type1_overwrite import apply_type1_correction
from problem_02_type2_new_row import apply_type2_move
from problem_03_type3_previous_value import apply_type3_region_change

_ASOF = (
    "SELECT name, department, salary, region FROM dim_employee_scd "
    "WHERE valid_from <= ? AND valid_to > ? ORDER BY employee_id"
)


def apply_all_three(conn: sqlite3.Connection) -> None:
    """Apply the Type 1, Type 2 and Type 3 changes of 2026-03-01."""
    apply_type1_correction(conn)
    apply_type2_move(conn)
    apply_type3_region_change(conn)


def as_of(conn: sqlite3.Connection, on: str) -> list[tuple]:
    """(name, department, salary, region) as of a date - one row each."""
    rows = conn.execute(_ASOF, (on, on)).fetchall()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def current_view(conn: sqlite3.Connection) -> list[tuple]:
    """(name, department, salary, region) for the 3 current rows."""
    rows = conn.execute(
        "SELECT name, department, salary, region FROM dim_employee_scd "
        "WHERE is_current = 1 ORDER BY employee_id"
    ).fetchall()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def dim_row_count(conn: sqlite3.Connection) -> int:
    """4 rows after all three changes: David 1, Frank 2, Irene 1."""
    return conn.execute("SELECT COUNT(*) FROM dim_employee_scd").fetchone()[0]
