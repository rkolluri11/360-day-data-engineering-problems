"""Day 42, problem 3: INTERSECT — the overlap is the answer.

INTERSECT returns only the rows present in both sides. It is the
"and" of set operations, and it replaces a join whenever the
question is just "who is in both lists?" — no join keys, no fanout
to worry about (contrast Day 32's join-key fanout: Apollo has two
tags, and a naive join would double-count it).

Engineering has 5 people; Apollo has 3 assignees; the overlap is
Alice, Bob, and Carol. Apollo and Beacon share exactly one person —
Alice, who is on both projects. The newsletter and the webinar share
3 signups: carol, david, and grace. INTERSECT always returns
distinct rows, so a person on Apollo twice (two assignments) still
counts once.
"""

from __future__ import annotations

import sqlite3


def engineering_on_apollo(conn: sqlite3.Connection) -> list[str]:
    """Engineering staff who are also on Apollo: Alice, Bob, Carol."""
    rows = conn.execute(
        "SELECT name FROM employees WHERE department = 'Engineering' "
        "INTERSECT "
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 1 "
        "ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def apollo_and_beacon(conn: sqlite3.Connection) -> list[str]:
    """People on both Apollo and Beacon: Alice Chen only."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 1 "
        "INTERSECT "
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 2 "
        "ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def apollo_or_beacon(conn: sqlite3.Connection) -> list[str]:
    """People on Apollo or Beacon (UNION, for contrast): 5 names, Alice once."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 1 "
        "UNION "
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 2 "
        "ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def apollo_and_beacon_union_all_count(conn: sqlite3.Connection) -> int:
    """UNION ALL of Apollo and Beacon assignees: 6 rows — Alice counted twice."""
    return conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 1 "
        "UNION ALL "
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 2)"
    ).fetchone()[0]


def newsletter_and_webinar(conn: sqlite3.Connection) -> list[str]:
    """Signed up for both the newsletter and the webinar: carol, david, grace."""
    rows = conn.execute(
        "SELECT email FROM newsletter INTERSECT SELECT email FROM webinar ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]
