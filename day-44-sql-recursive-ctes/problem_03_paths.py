"""Day 44, problem 3: path — the breadcrumb, built as you go.

The recursion carries a path string down with it, extending it one
level at a time: Alice Chen is "Grace Liu > Alice Chen", Leo
Garcia is "Mia Brown > Leo Garcia", David Kim is "Irene Novak >
David Kim". The path is just another column the recursive step
extends (t.path || ' > ' || e.name), so there is no string
juggling afterwards — and depth travels with it, so you can filter
or sort by level for free. Paths are how org charts, category
breadcrumbs, and file trees get rendered from a single query.
"""

from __future__ import annotations

import sqlite3

_PATH_CTE = """
WITH RECURSIVE chain(id, name, path, depth) AS (
  SELECT id, name, name, 0 FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.id, e.name, ch.path || ' > ' || e.name, ch.depth + 1
  FROM employees e JOIN chain ch ON e.manager_id = ch.id
)
"""


def paths(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """(name, path, depth) for all 13 people, shallowest first."""
    rows = conn.execute(
        _PATH_CTE + "SELECT name, path, depth FROM chain ORDER BY depth, name"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def path_for(conn: sqlite3.Connection, name: str) -> str:
    """The breadcrumb for one person: Alice -> 'Grace Liu > Alice Chen'."""
    row = conn.execute(
        _PATH_CTE + "SELECT path FROM chain WHERE name = ?", (name,)
    ).fetchone()
    return row[0]


def depth_for(conn: sqlite3.Connection, name: str) -> int:
    """How many levels below a root one person sits: Alice 1, Grace 0."""
    row = conn.execute(
        _PATH_CTE + "SELECT depth FROM chain WHERE name = ?", (name,)
    ).fetchone()
    return row[0]
