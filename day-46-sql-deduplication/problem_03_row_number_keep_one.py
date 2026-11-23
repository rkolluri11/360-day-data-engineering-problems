"""Day 46, problem 3: ROW_NUMBER keeps one per group.

The CRM import has 8 rows and 4 email addresses: David Kim 3
times (ids 1, 2, 7), Frank Lopez twice (3, 4), Irene Novak twice
(5, 6), Grace Liu once (8).

ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) numbers each
person's copies 1, 2, 3. Keep rn = 1: ids 1, 3, 5, 8 — 4 rows,
one per person. The ORDER BY inside the window is the whole
decision: ORDER BY id keeps the earliest import; ORDER BY
created DESC would keep the latest. PARTITION BY defines "the
same thing" — email here, not name: two different people can
share a name, and one person can have two emails.
"""

from __future__ import annotations

import sqlite3

_RANKED = """
SELECT *, ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) AS rn
FROM crm_contacts
"""


def ranked_contacts(conn: sqlite3.Connection) -> list[tuple]:
    """(id, name, email, rn) for all 8 rows, ordered by id."""
    rows = conn.execute(
        f"SELECT id, name, email, rn FROM ({_RANKED}) ORDER BY id"
    ).fetchall()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def keep_first_per_email(conn: sqlite3.Connection) -> list[tuple]:
    """The 4 survivors (rn = 1): ids 1, 3, 5, 8."""
    rows = conn.execute(
        f"SELECT id, name, email FROM ({_RANKED}) "
        "WHERE rn = 1 ORDER BY id"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def duplicate_rows(conn: sqlite3.Connection) -> list[tuple]:
    """The 4 rows to remove (rn > 1): ids 2, 4, 6, 7."""
    rows = conn.execute(
        f"SELECT id, name, email FROM ({_RANKED}) "
        "WHERE rn > 1 ORDER BY id"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def keep_latest_per_email(conn: sqlite3.Connection) -> list[tuple]:
    """Same dedup, latest import wins: ids 7, 4, 6, 8.

    The ORDER BY inside the window is the decision — change it
    and a different copy survives.
    """
    rows = conn.execute(
        "SELECT id, name, email FROM ("
        "SELECT *, ROW_NUMBER() OVER "
        "(PARTITION BY email ORDER BY id DESC) AS rn "
        "FROM crm_contacts) WHERE rn = 1 ORDER BY id"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def max_copies_per_email(conn: sqlite3.Connection) -> int:
    """David appears 3 times — the most copies any one person has."""
    return conn.execute(
        "SELECT MAX(c) FROM (SELECT COUNT(*) c FROM crm_contacts "
        "GROUP BY email)"
    ).fetchone()[0]
