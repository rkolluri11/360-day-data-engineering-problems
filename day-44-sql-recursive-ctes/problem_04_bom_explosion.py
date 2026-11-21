"""Day 44, problem 4: bill of materials — one laptop explodes into parts.

Laptop needs Screen, Keyboard, Memory x2, Battery, Chassis — and
each of those needs smaller parts. Quantities multiply down the
tree: Memory x2, each with Chip x8, is 16 chips. One laptop is 95
leaf parts across 6 types for $209.20: Glass 1 x $40, Backlight
2 x $5, Keycap 60 x $0.50, Chip 16 x $6, Cell 4 x $8, Screw
12 x $0.10.

The recursive step must carry the running quantity (b.qty *
comp.qty), or the explosion is wrong at every level below the
first. A leaf is a part that is never a parent: it has no rows in
the components table as a parent. Intermediate parts carry no unit
cost of their own — their cost is the sum of their children.
"""

from __future__ import annotations

import sqlite3


def _bom_cte(top: str, qty: int) -> str:
    return f"""
WITH RECURSIVE bom(part, qty, depth) AS (
  SELECT '{top}', {qty}, 0
  UNION ALL
  SELECT comp.child, b.qty * comp.qty, b.depth + 1
  FROM bom b JOIN components comp ON comp.parent = b.part
)
"""


def bom_explosion(conn: sqlite3.Connection, top: str = "Laptop", qty: int = 1) -> list[tuple[str, int, int]]:
    """Every (part, qty, depth) in the tree: 12 rows for 1 laptop."""
    rows = conn.execute(
        _bom_cte(top, qty) + "SELECT part, qty, depth FROM bom ORDER BY depth, part"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def bom_leaves(conn: sqlite3.Connection, top: str = "Laptop", qty: int = 1) -> list[tuple[str, int, float, float]]:
    """(leaf, qty, unit_cost, line_cost) for leaf parts only, by leaf name.

    A leaf is a part that never appears as a parent in components.
    """
    rows = conn.execute(
        _bom_cte(top, qty)
        + "SELECT b.part, b.qty, c.unit_cost, b.qty * c.unit_cost "
          "FROM bom b JOIN components c ON c.child = b.part "
          "WHERE b.part NOT IN (SELECT parent FROM components) "
          "ORDER BY b.part"
    ).fetchall()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def bom_leaf_total_units(conn: sqlite3.Connection, top: str = "Laptop", qty: int = 1) -> int:
    """Total leaf parts for the build: 95 for 1 laptop."""
    return conn.execute(
        _bom_cte(top, qty)
        + "SELECT SUM(qty) FROM bom "
          "WHERE part NOT IN (SELECT parent FROM components)"
    ).fetchone()[0]


def bom_leaf_total_cost(conn: sqlite3.Connection, top: str = "Laptop", qty: int = 1) -> float:
    """Total leaf cost for the build: $209.20 for 1 laptop."""
    return conn.execute(
        _bom_cte(top, qty)
        + "SELECT SUM(b.qty * c.unit_cost) FROM bom b "
          "JOIN components c ON c.child = b.part "
          "WHERE b.part NOT IN (SELECT parent FROM components)"
    ).fetchone()[0]
