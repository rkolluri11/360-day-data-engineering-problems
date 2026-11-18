"""Day 42, problem 1: UNION vs UNION ALL — dedup is the default.

UNION stacks two result sets and then removes duplicates; UNION ALL
stacks them and keeps every row. That one word is a correctness
decision, not a style choice: ask for "every department we know
about" and UNION gives 6 names; ask for "every department row from
both sources" and UNION ALL gives 10. Forget DISTINCT on the
employee side and UNION ALL gives 18 — Engineering counted five
times, once per engineer, plus once from the departments table.

Rule of thumb: UNION when the question is about a *set* of things
("which departments exist?"); UNION ALL when the question is about
*rows* ("how many department mentions are there?"). And both sides
of a set operation must return the same number of columns — SQLite
refuses a UNION of one column with two.
"""

from __future__ import annotations

import sqlite3


def employee_departments(conn: sqlite3.Connection) -> list[str]:
    """Distinct departments employees actually work in: 5, Legal included."""
    rows = conn.execute(
        "SELECT DISTINCT department FROM employees ORDER BY department"
    ).fetchall()
    return [r[0] for r in rows]


def department_names(conn: sqlite3.Connection) -> list[str]:
    """Departments in the departments (budget) table: 5, Operations included."""
    rows = conn.execute("SELECT dept_name FROM departments ORDER BY dept_name").fetchall()
    return [r[0] for r in rows]


def union_departments(conn: sqlite3.Connection) -> list[str]:
    """UNION of the two department lists: 6 names — Legal and Operations both survive."""
    rows = conn.execute(
        "SELECT DISTINCT department FROM employees "
        "UNION SELECT dept_name FROM departments ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def union_all_departments(conn: sqlite3.Connection) -> list[str]:
    """UNION ALL of the DISTINCT lists: 10 rows — the 4 shared names appear twice."""
    rows = conn.execute(
        "SELECT DISTINCT department FROM employees "
        "UNION ALL SELECT dept_name FROM departments"
    ).fetchall()
    return [r[0] for r in rows]


def union_all_without_distinct_count(conn: sqlite3.Connection) -> int:
    """UNION ALL with no DISTINCT: 18 rows — 13 employee rows + 5 department rows."""
    return conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT department FROM employees "
        "UNION ALL SELECT dept_name FROM departments)"
    ).fetchone()[0]


def engineering_mentions_without_distinct(conn: sqlite3.Connection) -> int:
    """'Engineering' in the no-DISTINCT UNION ALL: 6 times — 5 engineers + 1 budget row."""
    return conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT department FROM employees "
        "UNION ALL SELECT dept_name FROM departments) WHERE department = 'Engineering'"
    ).fetchone()[0]


def union_emails(conn: sqlite3.Connection) -> list[str]:
    """UNION of newsletter and webinar signups: 7 real people."""
    rows = conn.execute(
        "SELECT email FROM newsletter UNION SELECT email FROM webinar ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def union_all_email_count(conn: sqlite3.Connection) -> int:
    """UNION ALL of the two signup lists: 10 rows — 3 people signed up twice."""
    return conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT email FROM newsletter UNION ALL SELECT email FROM webinar)"
    ).fetchone()[0]


def union_mismatched_columns(conn: sqlite3.Connection) -> None:
    """UNION of 1 column with 2 columns: SQLite refuses — same arity required.

    Raises sqlite3.OperationalError: "SELECTs to the left and right of
    UNION do not have the same number of result columns".
    """
    conn.execute(
        "SELECT email FROM newsletter UNION SELECT email, 'webinar' FROM webinar"
    ).fetchall()
