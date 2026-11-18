"""Day 43, problem 5: combined — two semi-joins, one person.

The rungs compose. "Above their department average" is 5 people;
"has at least one order" is 3 people; the intersection, written
as a correlated subquery AND an EXISTS, is 1 person: Irene Novak
— above the Sales average at $175,000 and the only above-average
earner who ever sold anything. Grace, Alice, Karen and Mia are
above average but have no orders; David and Frank have orders
but are below their departments' averages.

The same composition answers "on Apollo but not on Beacon":
Bob Martinez and Carol Davis are on Apollo, Alice Chen is on
both, Grace Liu and David Kim are on Beacon only. Two EXISTS
clauses, one of them negated, and the answer is exact — no JOIN
fanout, no DISTINCT patch, no NULL trap, because neither list
is built by joining rows together.
"""

from __future__ import annotations

import sqlite3


def above_average_sellers(conn: sqlite3.Connection) -> list[str]:
    """Above their department average AND has at least one order: Irene only."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "WHERE e.salary > (SELECT AVG(salary) FROM employees x "
        "WHERE x.department = e.department) "
        "AND EXISTS (SELECT 1 FROM orders o WHERE o.employee_id = e.id) "
        "ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def above_average_non_sellers(conn: sqlite3.Connection) -> list[str]:
    """Above average but never sold anything: Grace, Alice, Karen, Mia."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "WHERE e.salary > (SELECT AVG(salary) FROM employees x "
        "WHERE x.department = e.department) "
        "AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.employee_id = e.id) "
        "ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def apollo_not_beacon(conn: sqlite3.Connection) -> list[str]:
    """On Apollo but not on Beacon: Bob Martinez, Carol Davis."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "WHERE EXISTS (SELECT 1 FROM assignments a JOIN projects p "
        "ON p.project_id = a.project_id "
        "WHERE a.employee_id = e.id AND p.project_name = 'Apollo') "
        "AND NOT EXISTS (SELECT 1 FROM assignments a JOIN projects p "
        "ON p.project_id = a.project_id "
        "WHERE a.employee_id = e.id AND p.project_name = 'Beacon') "
        "ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def sellers_below_average(conn: sqlite3.Connection) -> list[str]:
    """Have an order but are below their department average: David, Frank."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "WHERE e.salary <= (SELECT AVG(salary) FROM employees x "
        "WHERE x.department = e.department) "
        "AND EXISTS (SELECT 1 FROM orders o WHERE o.employee_id = e.id) "
        "ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]
