"""Day 46, problem 4: find them before you delete them.

GROUP BY + HAVING COUNT(*) > 1 lists the duplicates before
anything is deleted: David 3, Frank 2, Irene 2. Grace never
appears — HAVING filtered her out, which is exactly the point.

And clean the spelling before you compare: the raw import
(staged_raw, Day 41) writes "David Kim", "david kim", and
"  David Kim " — DISTINCT on the raw string sees three different
people; LOWER(TRIM(customer_raw)) sees one. Normalized counts:
David 3, Frank 3, Irene 2 — 3 distinct customers, not 8 rows.
"""

from __future__ import annotations

import sqlite3


def duplicate_emails(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """(email, count) for emails appearing more than once."""
    rows = conn.execute(
        "SELECT email, COUNT(*) FROM crm_contacts "
        "GROUP BY email HAVING COUNT(*) > 1 ORDER BY email"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def distinct_email_count(conn: sqlite3.Connection) -> int:
    """4 distinct email addresses in the 8-row import."""
    return conn.execute(
        "SELECT COUNT(DISTINCT email) FROM crm_contacts"
    ).fetchone()[0]


def total_contacts(conn: sqlite3.Connection) -> int:
    """8 rows in the import."""
    return conn.execute("SELECT COUNT(*) FROM crm_contacts").fetchone()[0]


def raw_distinct_customers(conn: sqlite3.Connection) -> list[str]:
    """DISTINCT on the raw dirty strings: 7 spellings, not 3 people.

    David has three spellings ("David Kim", "david kim",
    "  David Kim "), Frank two ("Frank Lopez", "FRANK LOPEZ "),
    Irene two ("Irene Novak", "irene novak") — 7 distinct strings
    for 3 people.
    """
    rows = conn.execute(
        "SELECT DISTINCT customer_raw FROM staged_raw ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def normalized_customers(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """(customer, count) after LOWER(TRIM()): David 3, Frank 3, Irene 2."""
    rows = conn.execute(
        "SELECT LOWER(TRIM(customer_raw)), COUNT(*) FROM staged_raw "
        "GROUP BY 1 ORDER BY 1"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def normalized_distinct_count(conn: sqlite3.Connection) -> int:
    """3 distinct customers once the spelling is cleaned."""
    return conn.execute(
        "SELECT COUNT(DISTINCT LOWER(TRIM(customer_raw))) FROM staged_raw"
    ).fetchone()[0]
