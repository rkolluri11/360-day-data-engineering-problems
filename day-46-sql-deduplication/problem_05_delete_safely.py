"""Day 46, problem 5: delete safely, keep the earliest.

DELETE the rows whose id is not the MIN(id) per email. Four
rows go — ids 2, 4, 6, 7 — and 4 stay (ids 1, 3, 5, 8).

Count before and after (8 -> 4), run the SELECT version of the
same predicate first, and do it in a transaction you can roll
back. There is no DELETE DISTINCT — DISTINCT only ever lives
in a SELECT, and a DELETE with no WHERE deletes the table.
The surviving row keeps the earliest id, not necessarily the
best data: if id 2 had the phone number and id 1 did not, the
survivor is poorer — merge fields first, then delete.
"""

from __future__ import annotations

import sqlite3

_KEEP_EARLIEST = (
    "id NOT IN (SELECT MIN(id) FROM crm_contacts GROUP BY email)"
)


def rows_to_delete(conn: sqlite3.Connection) -> list[int]:
    """The SELECT version first: ids 2, 4, 6, 7 — exactly the rows
    the DELETE will remove. Never delete what you have not listed."""
    rows = conn.execute(
        f"SELECT id FROM crm_contacts WHERE {_KEEP_EARLIEST} ORDER BY id"
    ).fetchall()
    return [r[0] for r in rows]


def delete_duplicates_keep_earliest(conn: sqlite3.Connection) -> int:
    """Delete the duplicates, keep MIN(id) per email. Returns the
    number of rows deleted: 4. Runs in the caller's transaction —
    commit or roll back as you choose."""
    cur = conn.execute(
        f"DELETE FROM crm_contacts WHERE {_KEEP_EARLIEST}"
    )
    return cur.rowcount


def count_after_delete(conn: sqlite3.Connection) -> int:
    """4 rows remain after the delete."""
    return conn.execute("SELECT COUNT(*) FROM crm_contacts").fetchone()[0]


def survivors_after_delete(conn: sqlite3.Connection) -> list[tuple]:
    """The 4 survivors: ids 1, 3, 5, 8, one per email."""
    rows = conn.execute(
        "SELECT id, name, email FROM crm_contacts ORDER BY id"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def delete_in_transaction(conn: sqlite3.Connection) -> tuple[int, int]:
    """Delete inside an explicit transaction and commit: returns
    (deleted, remaining) = (4, 4)."""
    conn.execute("BEGIN")
    deleted = delete_duplicates_keep_earliest(conn)
    conn.execute("COMMIT")
    return deleted, count_after_delete(conn)
