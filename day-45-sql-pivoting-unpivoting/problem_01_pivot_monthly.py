"""Day 45, problem 1: the pivot — one row per seller, one column per month.

SQLite has no PIVOT keyword, so the pivot is conditional
aggregation: SUM(CASE WHEN the month is '01' THEN amount END)
for January, and so on for February and March. The same 8 orders
(7 priced, total $81,000) become 3 rows and 9 cells:

- David Kim: Jan $20,000, Feb $0, Mar $0 — total $20,000
- Frank Lopez: Jan $15,000, Feb $5,000, Mar $9,000 — $29,000
- Irene Novak: Jan $0, Feb $32,000, Mar $0 — $32,000

Month totals: Jan $35,000, Feb $37,000, Mar $9,000.
"""

from __future__ import annotations

import sqlite3

_PIVOT = """
SELECT e.name,
  COALESCE(SUM(CASE WHEN strftime('%m', o.order_date) = '01' THEN o.amount END), 0) AS jan,
  COALESCE(SUM(CASE WHEN strftime('%m', o.order_date) = '02' THEN o.amount END), 0) AS feb,
  COALESCE(SUM(CASE WHEN strftime('%m', o.order_date) = '03' THEN o.amount END), 0) AS mar
FROM employees e JOIN orders o ON o.employee_id = e.id
GROUP BY e.name
ORDER BY e.name
"""


def pivot_monthly(conn: sqlite3.Connection) -> list[tuple[str, int, int, int]]:
    """(name, jan, feb, mar) per seller, missing months as 0."""
    rows = conn.execute(_PIVOT).fetchall()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def pivot_with_totals(conn: sqlite3.Connection) -> list[tuple[str, int, int, int, int]]:
    """The pivot plus a per-seller total column: 20000 / 29000 / 32000."""
    rows = conn.execute(
        _PIVOT.replace(
            "AS mar\nFROM",
            "AS mar,\n  SUM(o.amount) AS total\nFROM",
        )
    ).fetchall()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


def month_totals(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """(month, total) in the long table: Jan 35000, Feb 37000, Mar 9000."""
    rows = conn.execute(
        "SELECT strftime('%m', order_date), SUM(amount) FROM orders "
        "GROUP BY 1 ORDER BY 1"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def grand_total(conn: sqlite3.Connection) -> int:
    """The long table's total: $81,000 — the pivot must reconcile to it."""
    return conn.execute("SELECT SUM(amount) FROM orders").fetchone()[0]


def pivot_reconciles(conn: sqlite3.Connection) -> bool:
    """Sum of every pivoted cell equals the long table's grand total."""
    cells = sum(j + f + m for _, j, f, m in pivot_monthly(conn))
    return cells == grand_total(conn)
