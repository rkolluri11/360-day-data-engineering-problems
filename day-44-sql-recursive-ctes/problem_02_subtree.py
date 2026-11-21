"""Day 44, problem 2: subtree — everyone under one manager.

Anchor the recursion at one person and it returns their whole
team, at every depth: the anchor row is part of the answer, not
just the starting line. Grace's team is 5 people (Grace plus her
4 direct reports), $667,000 in salary. Same query, different
anchor: Irene's team is 3 people, $368,000; Karen's 2, $280,000;
Mia's 2, $180,000; Nina's 1, $125,000.

A headcount query that counts only the recursive rows undercounts
by one — it forgets the anchor. The salary rollup is a plain SUM
over the recursive result: no GROUP BY gymnastics, no per-level
UNIONs.
"""

from __future__ import annotations

import sqlite3


def _subtree_cte(manager_id: int) -> str:
    return f"""
WITH RECURSIVE sub(id, name, salary, depth) AS (
  SELECT id, name, salary, 0 FROM employees WHERE id = {manager_id}
  UNION ALL
  SELECT e.id, e.name, e.salary, s.depth + 1
  FROM employees e JOIN sub s ON e.manager_id = s.id
)
"""


def subtree(conn: sqlite3.Connection, manager_id: int) -> list[tuple[str, int]]:
    """(name, depth) for the whole team under one manager, anchor included."""
    rows = conn.execute(
        _subtree_cte(manager_id) + "SELECT name, depth FROM sub ORDER BY depth, name"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def subtree_headcount(conn: sqlite3.Connection, manager_id: int) -> int:
    """People in the team, anchor included: Grace 5, Irene 3, Nina 1."""
    return conn.execute(
        _subtree_cte(manager_id) + "SELECT COUNT(*) FROM sub"
    ).fetchone()[0]


def subtree_salary_total(conn: sqlite3.Connection, manager_id: int) -> int:
    """Combined salary of the whole team: Grace $667,000, Irene $368,000."""
    return conn.execute(
        _subtree_cte(manager_id) + "SELECT SUM(salary) FROM sub"
    ).fetchone()[0]


def descendants_only(conn: sqlite3.Connection, manager_id: int) -> list[str]:
    """Everyone under the manager, anchor excluded: Grace's 4 reports.

    The deliberate version of the 2 AM mistake — filter depth > 0
    on purpose, never by forgetting the anchor is in the result.
    """
    rows = conn.execute(
        _subtree_cte(manager_id) + "SELECT name FROM sub WHERE depth > 0 ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def all_subtree_totals(conn: sqlite3.Connection) -> list[tuple[str, int, int]]:
    """(manager, headcount, salary total) for each of the 5 roots."""
    out = []
    for manager_id, name in [(1, "Grace Liu"), (8, "Irene Novak"), (10, "Karen White"),
                             (12, "Mia Brown"), (13, "Nina Patel")]:
        out.append((
            name,
            subtree_headcount(conn, manager_id),
            subtree_salary_total(conn, manager_id),
        ))
    return sorted(out)
