"""Day 43, problem 4: EXISTS with a threshold — "does this group have one?".

EXISTS does not have to stand alone: the subquery can carry its
own filter, so the outer question becomes "does this department
have at least one person over $150,000?" instead of "what is
everyone's salary?". The answer is 3 departments — Data (Karen
White, $160,000), Engineering (Grace Liu, $190,000), Sales
(Irene Novak, $175,000). HR tops out at Mia Brown's $105,000,
so it does not qualify; Legal is not in the departments table
at all (see below).

The same shape answers a dozen pipeline questions: which
customers have at least one failed payment, which tables have at
least one row past its SLA, which services logged at least one
error today. EXISTS stops at the first match, so it never scans
the whole group once the answer is yes — and unlike a JOIN it
returns the department once, even if three people clear the bar.
Note the departments table itself has no Legal row (Day 42):
Legal has people but no budget row, so it can never appear in
either list here — only HR and Operations come back empty.
"""

from __future__ import annotations

import sqlite3


def departments_with_high_earner(conn: sqlite3.Connection) -> list[str]:
    """Departments with at least one earner over $150,000: 3."""
    rows = conn.execute(
        "SELECT dept_name FROM departments d "
        "WHERE EXISTS (SELECT 1 FROM employees e "
        "WHERE e.department = d.dept_name AND e.salary > 150000) "
        "ORDER BY dept_name"
    ).fetchall()
    return [r[0] for r in rows]


def departments_without_high_earner(conn: sqlite3.Connection) -> list[str]:
    """Departments with no earner over $150,000: HR, Operations.

    Operations has a budget row but no employees at all. Legal
    never appears: it has people but no row in the departments
    table (Day 42), so EXISTS/NOT EXISTS over departments cannot
    see it."""
    rows = conn.execute(
        "SELECT dept_name FROM departments d "
        "WHERE NOT EXISTS (SELECT 1 FROM employees e "
        "WHERE e.department = d.dept_name AND e.salary > 150000) "
        "ORDER BY dept_name"
    ).fetchall()
    return [r[0] for r in rows]


def high_earners(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """The earners over $150,000 themselves: 3 people."""
    rows = conn.execute(
        "SELECT name, department, salary FROM employees "
        "WHERE salary > 150000 ORDER BY department, name"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def department_top_salary(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """Top salary per department that has employees, ordered by department."""
    rows = conn.execute(
        "SELECT department, MAX(salary) FROM employees "
        "GROUP BY department ORDER BY department"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]
