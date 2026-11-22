"""Day 45, problem 2: NULL is not zero — the pending quote.

SUM over no rows is NULL, not 0, so a missing month shows as
blank unless you COALESCE it to 0. David Kim in February is the
trap: one order (order 7, a pending quote), amount NULL.

- COUNT(*) = 1 order, COUNT(amount) = 0 priced sales, SUM = NULL.
- COALESCE the cell to $0 for the dashboard — but it was a quote,
  not a $0 sale. A dashboard that cannot tell those apart will
  one day report "no work" for a seller with a quote out.

The same NULL-vs-zero split shows in the raw pivot: without
COALESCE, David's Feb and Mar cells and Irene's Jan and Mar cells
are NULL, not 0 — 4 NULL cells out of 9.
"""

from __future__ import annotations

import sqlite3

_RAW_PIVOT = """
SELECT e.name,
  SUM(CASE WHEN strftime('%m', o.order_date) = '01' THEN o.amount END) AS jan,
  SUM(CASE WHEN strftime('%m', o.order_date) = '02' THEN o.amount END) AS feb,
  SUM(CASE WHEN strftime('%m', o.order_date) = '03' THEN o.amount END) AS mar
FROM employees e JOIN orders o ON o.employee_id = e.id
GROUP BY e.name
ORDER BY e.name
"""


def raw_pivot(conn: sqlite3.Connection) -> list[tuple]:
    """The pivot without COALESCE: missing months are NULL, not 0."""
    return [tuple(r) for r in conn.execute(_RAW_PIVOT).fetchall()]


def null_cells(conn: sqlite3.Connection) -> int:
    """How many of the 9 pivoted cells are NULL before COALESCE: 4."""
    rows = raw_pivot(conn)
    return sum(1 for r in rows for v in r[1:] if v is None)


def david_february(conn: sqlite3.Connection) -> tuple[int, int, int | None]:
    """(order count, priced count, sum) for David Kim in Feb: (1, 0, None)."""
    row = conn.execute(
        "SELECT COUNT(*), COUNT(amount), SUM(amount) FROM orders "
        "WHERE employee_id = 6 AND strftime('%m', order_date) = '02'"
    ).fetchone()
    return (row[0], row[1], row[2])


def priced_orders(conn: sqlite3.Connection) -> int:
    """Orders with a real amount: 7 of the 8 orders."""
    return conn.execute("SELECT COUNT(amount) FROM orders").fetchone()[0]


def all_orders(conn: sqlite3.Connection) -> int:
    """Every order row, priced or pending: 8."""
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
