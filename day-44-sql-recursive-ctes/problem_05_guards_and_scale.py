"""Day 44, problem 5: the guard — cycles and scale.

A part that contains itself — directly, or three levels down —
makes UNION ALL loop forever, because every round finds "new"
rows. Guard it two ways: cap the depth in the recursive step
(WHERE depth < cap), and use UNION instead of UNION ALL when rows
can repeat, so a repeated row stops the recursion.

With the guard in place, scale is free: 10 laptops is 950 leaf
parts for $2,092.00 — same query, anchor quantity 10. The depth
cap is also your canary: if a traversal ever hits it, the data has
a cycle (or a tree deeper than you believed), and that is worth
knowing before the query runs in production.
"""

from __future__ import annotations

import sqlite3

from problem_04_bom_explosion import bom_leaf_total_cost, bom_leaf_total_units


def bom_scaled(conn: sqlite3.Connection, top: str, n: int) -> tuple[int, float]:
    """(leaf units, leaf cost) for n top-level items: 10 laptops -> (950, 2092.0)."""
    return (
        bom_leaf_total_units(conn, top, n),
        bom_leaf_total_cost(conn, top, n),
    )


def bom_with_depth_cap(conn: sqlite3.Connection, top: str = "Laptop", cap: int = 1) -> list[tuple[str, int, int]]:
    """(part, qty, depth) with the recursion stopped at depth <= cap.

    Cap 1 returns the laptop plus its 5 sub-assemblies — 6 rows —
    and never descends to the leaves. The cap is the guard: the
    recursive step only fires while the parent depth is below it.
    """
    rows = conn.execute(
        f"""
WITH RECURSIVE bom(part, qty, depth) AS (
  SELECT '{top}', 1, 0
  UNION ALL
  SELECT comp.child, b.qty * comp.qty, b.depth + 1
  FROM bom b JOIN components comp ON comp.parent = b.part
  WHERE b.depth < {cap}
)
SELECT part, qty, depth FROM bom ORDER BY depth, part
"""
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def distinct_parts(conn: sqlite3.Connection, top: str = "Laptop") -> list[str]:
    """Every distinct part in the tree, via UNION dedup: 12 for a laptop.

    UNION (not UNION ALL) collapses repeated rows — the second half
    of the cycle guard. A part reached twice still appears once.
    """
    rows = conn.execute(
        f"""
WITH RECURSIVE bom(part) AS (
  SELECT '{top}'
  UNION
  SELECT comp.child
  FROM bom b JOIN components comp ON comp.parent = b.part
)
SELECT part FROM bom ORDER BY part
"""
    ).fetchall()
    return [r[0] for r in rows]


def cyclic_traversal_terminates(conn: sqlite3.Connection, cap: int = 9) -> tuple[int, int]:
    """Run a guarded traversal over a deliberately cyclic parts list.

    Adds Glass -> Laptop to a scratch copy of components, closing a
    loop (Laptop -> Screen -> Glass -> Laptop -> ...). With the
    depth cap the recursion stops: it returns (row count, max depth)
    instead of looping forever. Without the cap this query would
    never return — which is exactly why the guard exists.
    """
    conn.execute("DROP TABLE IF EXISTS components_cycle")
    conn.execute(
        "CREATE TABLE components_cycle (parent TEXT, child TEXT, qty INTEGER, unit_cost REAL)"
    )
    conn.execute("INSERT INTO components_cycle SELECT parent, child, qty, unit_cost FROM components")
    conn.execute("INSERT INTO components_cycle VALUES ('Glass', 'Laptop', 1, NULL)")
    rows = conn.execute(
        f"""
WITH RECURSIVE bom(part, qty, depth) AS (
  SELECT 'Laptop', 1, 0
  UNION ALL
  SELECT comp.child, b.qty * comp.qty, b.depth + 1
  FROM bom b JOIN components_cycle comp ON comp.parent = b.part
  WHERE b.depth < {cap}
)
SELECT COUNT(*), MAX(depth) FROM bom
"""
    ).fetchone()
    conn.execute("DROP TABLE components_cycle")
    return (rows[0], rows[1])
