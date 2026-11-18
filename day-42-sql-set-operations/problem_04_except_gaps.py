"""Day 42, problem 4: EXCEPT — what's missing is the finding.

EXCEPT returns rows in the left side that are not in the right side.
It is the "not" of set operations, and direction is everything:
newsletter EXCEPT webinar is alice and bob; webinar EXCEPT
newsletter is frank and henry — a different answer from a swapped
query, with no error to warn you.

The production uses are gap hunts. Engineering minus Apollo is
Grace and Henry — the two engineers not staffed on the flagship
project. Employee departments minus the departments table is Legal —
a department with a person (Nina Patel) and no budget row, the kind
of master-data gap that silently drops a team from every
department-level report until someone asks why Legal never appears.
"""

from __future__ import annotations

import sqlite3


def engineering_not_on_apollo(conn: sqlite3.Connection) -> list[str]:
    """Engineering staff NOT on Apollo: Grace Liu, Henry Wong."""
    rows = conn.execute(
        "SELECT name FROM employees WHERE department = 'Engineering' "
        "EXCEPT "
        "SELECT e.name FROM employees e "
        "JOIN assignments a ON a.employee_id = e.id WHERE a.project_id = 1 "
        "ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def newsletter_only(conn: sqlite3.Connection) -> list[str]:
    """Newsletter signups who never registered for the webinar: alice, bob."""
    rows = conn.execute(
        "SELECT email FROM newsletter EXCEPT SELECT email FROM webinar ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def webinar_only(conn: sqlite3.Connection) -> list[str]:
    """Webinar registrants not on the newsletter: frank, henry.

    Note this is NOT the mirror of newsletter_only — EXCEPT is
    directional, and swapping the sides changes the answer.
    """
    rows = conn.execute(
        "SELECT email FROM webinar EXCEPT SELECT email FROM newsletter ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def departments_without_budget_row(conn: sqlite3.Connection) -> list[str]:
    """Employee departments with no row in the departments table: Legal only.

    Legal has a person (Nina Patel) but no budget row — a master-data
    gap that drops Legal from every department-level rollup.
    """
    rows = conn.execute(
        "SELECT DISTINCT department FROM employees "
        "EXCEPT SELECT dept_name FROM departments ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def departments_without_employees(conn: sqlite3.Connection) -> list[str]:
    """Departments-table rows with no employees: Operations only.

    The reverse gap: a budget exists, but nobody works there.
    """
    rows = conn.execute(
        "SELECT dept_name FROM departments "
        "EXCEPT SELECT DISTINCT department FROM employees ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]
