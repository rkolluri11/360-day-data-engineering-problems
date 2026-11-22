"""Day 45, problem 3: the same pivot, a different axis — seller x region.

A pivot is not tied to months. Swap the CASE WHEN condition and
the same 8 orders pivot by region instead:

- David Kim: East $20,000, West $0 (his one West order is the
  pending quote, amount NULL — SUM ignores it)
- Frank Lopez: East $9,000, West $20,000
- Irene Novak: East $25,000, West $7,000

Region totals: East $54,000, West $27,000 — again $81,000 in
total. Any pivot over the same orders must reconcile to the same
grand total, whichever axis you choose.
"""

from __future__ import annotations

import sqlite3


def pivot_region(conn: sqlite3.Connection) -> list[tuple[str, int, int]]:
    """(name, east, west) per seller, missing regions as 0."""
    rows = conn.execute(
        """
        SELECT e.name,
          COALESCE(SUM(CASE WHEN o.region = 'East' THEN o.amount END), 0) AS east,
          COALESCE(SUM(CASE WHEN o.region = 'West' THEN o.amount END), 0) AS west
        FROM employees e JOIN orders o ON o.employee_id = e.id
        GROUP BY e.name
        ORDER BY e.name
        """
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def region_totals(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """(region, total) in the long table: East 54000, West 27000."""
    rows = conn.execute(
        "SELECT region, SUM(amount) FROM orders GROUP BY region ORDER BY region"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def pivot_region_reconciles(conn: sqlite3.Connection) -> bool:
    """Sum of every region-pivoted cell equals the $81,000 grand total."""
    cells = sum(e + w for _, e, w in pivot_region(conn))
    return cells == conn.execute("SELECT SUM(amount) FROM orders").fetchone()[0]
