"""Day 43, problem 2: the correlated subquery — one average per row.

A plain subquery runs once. A correlated subquery runs once per
row, because it references the outer row: ``WHERE x.department =
e.department`` makes the average recompute for each employee's
own department. That is the whole trick behind "above average
for their group" — there is no single company average that
answers it, and a GROUP BY cannot compare a row to its own
group's average in the same step.

The numbers: Engineering averages $133,400 (5 people), Sales
$122,666.67 (3), Data $140,000 (2), HR $90,000 (2), Legal
$125,000 (1 — Nina Patel alone). Above their own department
average: Grace Liu ($190,000) and Alice Chen ($145,000) in
Engineering, Irene Novak ($175,000) in Sales, Karen White
($160,000) in Data, Mia Brown ($105,000) in HR — 5 people.
Nina is not above her average: she IS the average, and a strict
``>`` leaves her out. The correlation is the point: change
``e.department`` to a fixed value and every row is judged
against the wrong group.
"""

from __future__ import annotations

import sqlite3


def department_averages(conn: sqlite3.Connection) -> list[tuple[str, float, int]]:
    """Average salary and headcount per department, ordered by department."""
    rows = conn.execute(
        "SELECT department, AVG(salary), COUNT(*) FROM employees "
        "GROUP BY department ORDER BY department"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def above_department_average(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Employees earning above their own department's average: 5 people."""
    rows = conn.execute(
        "SELECT e.name, e.department, e.salary FROM employees e "
        "WHERE e.salary > (SELECT AVG(salary) FROM employees x "
        "WHERE x.department = e.department) "
        "ORDER BY e.department, e.name"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def above_company_average(conn: sqlite3.Connection) -> list[str]:
    """Employees above the single company-wide average — the wrong comparison.

    The company average is $124,615.38, so this returns 5 names
    (Alice, Grace, Irene, Karen, Nina) and wrongly includes Nina —
    who is exactly her own department's average, not above it —
    while wrongly dropping Mia, who beats HR's $90,000 average.
    """
    rows = conn.execute(
        "SELECT name FROM employees "
        "WHERE salary > (SELECT AVG(salary) FROM employees) ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def company_average(conn: sqlite3.Connection) -> float:
    """Company-wide average salary: $124,615.38."""
    return conn.execute("SELECT AVG(salary) FROM employees").fetchone()[0]


def legal_average_is_nina(conn: sqlite3.Connection) -> tuple[float, int]:
    """Legal's average and headcount: $125,000, 1 — Nina is her own average."""
    row = conn.execute(
        "SELECT AVG(salary), COUNT(*) FROM employees WHERE department = 'Legal'"
    ).fetchone()
    return (row[0], row[1])
