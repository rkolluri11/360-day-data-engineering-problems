"""Day 44, problem 1: org levels — the anchor and the recursive step.

A tree is rows that point at each other: manager_id points at
another employee. A JOIN walks exactly one level. A recursive CTE
walks until nothing is left: an anchor (the starting rows), a
recursive step (one more level, joined back to the CTE itself),
and UNION ALL stacking the levels.

The anchor here is the 5 people with no manager — Grace, Irene,
Karen, Mia, Nina — at depth 0. One recursive step finds their 8
direct reports at depth 1. Max depth is 1: this org is flat.
Depth is data, not code — the day a third level appears, this
query finds it, while a query written as N self-JOINs silently
drops the new floor.
"""

from __future__ import annotations

import sqlite3

_LEVELS_CTE = """
WITH RECURSIVE tree(id, name, depth) AS (
  SELECT id, name, 0 FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.id, e.name, t.depth + 1
  FROM employees e JOIN tree t ON e.manager_id = t.id
)
"""


def org_levels(conn: sqlite3.Connection) -> list[tuple[int, int]]:
    """(depth, headcount) per level: depth 0 has 5, depth 1 has 8."""
    rows = conn.execute(
        _LEVELS_CTE + "SELECT depth, COUNT(*) FROM tree GROUP BY depth ORDER BY depth"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def roots(conn: sqlite3.Connection) -> list[str]:
    """The 5 people with no manager: the anchor rows, depth 0."""
    rows = conn.execute(
        _LEVELS_CTE + "SELECT name FROM tree WHERE depth = 0 ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def people_at_depth(conn: sqlite3.Connection, depth: int) -> list[str]:
    """Everyone sitting at one level of the tree, by name."""
    rows = conn.execute(
        _LEVELS_CTE + "SELECT name FROM tree WHERE depth = ? ORDER BY name",
        (depth,),
    ).fetchall()
    return [r[0] for r in rows]


def max_depth(conn: sqlite3.Connection) -> int:
    """Deepest level in the org: 1 — a flat org, two levels total."""
    return conn.execute(_LEVELS_CTE + "SELECT MAX(depth) FROM tree").fetchone()[0]


def direct_reports(conn: sqlite3.Connection, manager_id: int) -> list[str]:
    """One level only, no recursion: the manager's direct reports.

    The contrast that motivates the whole day — this answers one
    level; the recursive CTE answers every level below.
    """
    rows = conn.execute(
        "SELECT name FROM employees WHERE manager_id = ? ORDER BY name",
        (manager_id,),
    ).fetchall()
    return [r[0] for r in rows]
