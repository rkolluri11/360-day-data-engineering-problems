"""Day 32 - Problem 4: join-key fanout — when one row becomes many, and
your totals lie.

A join multiplies rows: an employee with 2 assignments appears twice
in the joined output. That fanout is correct for listing, and poison
for aggregating. The classic production bug: join assignments to a
dimension that itself has multiple rows per key (project_tags — Apollo
has 2 tags), then SUM the hours, and Apollo's hours double.

Beginner foothold: fanout is a photocopier. Joining through a table
with 2 matching rows photocopies each input row twice. Counts and
sums over the photocopied output are wrong unless you account for it.

Three functions, one lesson:
1. The fanout itself: joined assignment rows (8) vs employees (13).
2. DISTINCT as the counting fix: Alice's distinct projects (2).
3. The money trap: naive SUM over the tags join (131, wrong) vs SUM
   over the assignments alone (96, right) — aggregate the fact table
   BEFORE joining a fanout dimension, never after.
"""

from __future__ import annotations

import sqlite3


def joined_assignment_rows(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """One row per assignment, employee + project + hours.
    Alice and Carol each appear twice — that is fanout, not a bug."""
    return conn.execute(
        """
        SELECT e.name, p.project_name, a.hours
        FROM employees e
        JOIN assignments a ON e.id = a.employee_id
        JOIN projects p ON a.project_id = p.project_id
        ORDER BY e.name ASC, p.project_name ASC
        """
    ).fetchall()


def distinct_projects_for(conn: sqlite3.Connection, employee_name: str) -> list[str]:
    """Distinct projects one employee works on — DISTINCT undoes the
    fanout for counting purposes."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT p.project_name
            FROM employees e
            JOIN assignments a ON e.id = a.employee_id
            JOIN projects p ON a.project_id = p.project_id
            WHERE e.name = ?
            ORDER BY p.project_name ASC
            """,
            (employee_name,),
        ).fetchall()
    ]


def naive_total_hours_with_tags(conn: sqlite3.Connection) -> int:
    """WRONG total: SUM(hours) after joining project_tags. Apollo's
    35 hours are counted twice (2 tags) -> 131 instead of 96.
    Kept deliberately to show the trap."""
    return conn.execute(
        """
        SELECT SUM(a.hours)
        FROM assignments a
        JOIN project_tags t ON a.project_id = t.project_id
        """
    ).fetchone()[0]


def true_total_hours(conn: sqlite3.Connection) -> int:
    """RIGHT total: SUM(hours) over assignments alone, before any
    fanout dimension is joined."""
    return conn.execute("SELECT SUM(hours) FROM assignments").fetchone()[0]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print(f"joined assignment rows: {len(joined_assignment_rows(conn))}")
    print("Alice's distinct projects:", distinct_projects_for(conn, "Alice Chen"))
    print("naive hours (with tags join):", naive_total_hours_with_tags(conn))
    print("true hours (assignments alone):", true_total_hours(conn))
