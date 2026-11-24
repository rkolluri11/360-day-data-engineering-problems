"""Day 47, problem 5: the MERGE batch - one staging table, one transaction.

stg_employee_changes holds the whole 2026-03-01 batch: David Type 1,
Frank Type 2, Irene Type 3, and Grace Liu as a brand-new row. MERGE
matches staging to the current rows on employee_id and does the
right thing per change_type - but one honest limit: a single MERGE
cannot both close Frank's old row AND insert his new one, because
one matched source row produces one target action. So the batch is
MERGE for the close (and the Type 1 / Type 3 updates, and the new
insert) plus a separate INSERT for the new Type 2 version, all inside
one transaction. After the batch: 5 rows, 4 current, Grace in place.

The MERGE below is written for Snowflake / SQL Server, which have
MERGE. SQLite does not - the Python here is the SQLite equivalent,
step by step, and the tests verify the same end state.
"""

from __future__ import annotations

import sqlite3

MERGE_SQL = """
MERGE INTO dim_employee_scd AS target
USING stg_employee_changes AS source
  ON target.employee_id = source.employee_id
 AND target.is_current = 1
WHEN MATCHED AND source.change_type = 'type1' THEN
  UPDATE SET salary = source.salary
WHEN MATCHED AND source.change_type = 'type2' THEN
  UPDATE SET valid_to = source.effective_date, is_current = 0
WHEN MATCHED AND source.change_type = 'type3' THEN
  UPDATE SET previous_region = target.region, region = source.region
WHEN NOT MATCHED THEN
  INSERT (employee_id, name, department, region, salary,
          previous_region, valid_from, valid_to, is_current)
  VALUES (source.employee_id, source.name, source.department,
          source.region, source.salary, NULL,
          source.effective_date, '9999-12-31', 1);
-- One MERGE cannot both close the old Type 2 row and insert the
-- new one, so the INSERT below runs in the same transaction.
-- Then, in the SAME transaction, insert the new Type 2 version:
-- INSERT INTO dim_employee_scd SELECT ... FROM stg_employee_changes
-- WHERE change_type = 'type2' (valid_from = effective_date, current).
"""


def apply_merge_batch(conn: sqlite3.Connection) -> None:
    """Apply every staging row in one transaction, per change_type."""
    rows = conn.execute(
        "SELECT employee_id, name, department, region, salary, "
        "change_type, effective_date FROM stg_employee_changes "
        "ORDER BY employee_id"
    ).fetchall()
    for eid, name, dept, region, salary, ctype, eff in rows:
        if ctype == "type1":
            conn.execute(
                "UPDATE dim_employee_scd SET salary = ? "
                "WHERE employee_id = ? AND is_current = 1",
                (salary, eid),
            )
        elif ctype == "type2":
            conn.execute(
                "UPDATE dim_employee_scd SET valid_to = ?, is_current = 0 "
                "WHERE employee_id = ? AND is_current = 1",
                (eff, eid),
            )
            conn.execute(
                "INSERT INTO dim_employee_scd VALUES "
                "(?, ?, ?, ?, ?, NULL, ?, '9999-12-31', 1)",
                (eid, name, dept, region, salary, eff),
            )
        elif ctype == "type3":
            conn.execute(
                "UPDATE dim_employee_scd "
                "SET previous_region = region, region = ? "
                "WHERE employee_id = ? AND is_current = 1",
                (region, eid),
            )
        elif ctype == "new":
            conn.execute(
                "INSERT INTO dim_employee_scd VALUES "
                "(?, ?, ?, ?, ?, NULL, ?, '9999-12-31', 1)",
                (eid, name, dept, region, salary, eff),
            )
        else:  # pragma: no cover - staging holds only the four types
            raise ValueError(f"unknown change_type {ctype!r}")
    conn.commit()


def batch_totals(conn: sqlite3.Connection) -> tuple:
    """(total rows, current rows) after the batch: (5, 4)."""
    total = conn.execute("SELECT COUNT(*) FROM dim_employee_scd").fetchone()[0]
    current = conn.execute(
        "SELECT COUNT(*) FROM dim_employee_scd WHERE is_current = 1"
    ).fetchone()[0]
    return (total, current)


def grace_row(conn: sqlite3.Connection) -> tuple:
    """Grace's new row: Engineering, West, $190,000, from 2026-03-01."""
    r = conn.execute(
        "SELECT department, region, salary, valid_from "
        "FROM dim_employee_scd WHERE employee_id = 1"
    ).fetchone()
    return (r[0], r[1], r[2], r[3])
