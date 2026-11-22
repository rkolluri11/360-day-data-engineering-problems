"""Day 45, problem 5: the missing column and the round trip.

Two things a hard-coded pivot cannot do:

1. Grow. The pivot in problem 1 has columns for months 01, 02,
   03 — the months present in orders. A first April order would
   be silently dropped: no error, no column, no dollars in the
   total. The fix is to read the categories from the data and
   build the pivot columns dynamically (or pivot in the
   reporting layer, which already does this).

2. Come back. Pivot the 8 orders, then unpivot the result, and
   you do not get the orders table back: order ids, regions and
   dates are gone, and the pending quote vanished entirely — 8
   orders became 5 priced rows. The wide table is a report, not
   a source of truth. And a total row must never be pivoted in:
   pivoting a row that already holds the $81,000 total would
   count it twice ($162,000).
"""

from __future__ import annotations

import sqlite3

from problem_01_pivot_monthly import pivot_monthly
from problem_04_unpivot import unpivot_priced


def months_present(conn: sqlite3.Connection) -> list[str]:
    """Distinct months in orders, in order: ['01', '02', '03'] — no April."""
    rows = conn.execute(
        "SELECT DISTINCT strftime('%m', order_date) FROM orders ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def dynamic_pivot(conn: sqlite3.Connection, months: list[str]) -> list[tuple]:
    """Build the pivot's CASE WHEN columns from a month list.

    For the months actually present this returns exactly the
    problem-1 pivot; for a month with no orders (e.g. '04') it
    returns a column of zeros — the shape exists, the data does
    not, which is the honest way to show a missing month.
    """
    cols = ",\n  ".join(
        f"COALESCE(SUM(CASE WHEN strftime('%m', o.order_date) = '{m}' "
        f"THEN o.amount END), 0) AS m{m}"
        for m in months
    )
    rows = conn.execute(
        f"SELECT e.name,\n  {cols}\n"
        "FROM employees e JOIN orders o ON o.employee_id = e.id "
        "GROUP BY e.name ORDER BY e.name"
    ).fetchall()
    return [tuple(r) for r in rows]


def roundtrip_row_count(conn: sqlite3.Connection) -> int:
    """Rows after pivot-then-unpivot (priced only): 5, not 8."""
    return len(unpivot_priced(conn))


def original_order_count(conn: sqlite3.Connection) -> int:
    """Rows in the long table the pivot came from: 8."""
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


def roundtrip_loses_rows(conn: sqlite3.Connection) -> bool:
    """True: the round trip does not restore the orders table."""
    return roundtrip_row_count(conn) != original_order_count(conn)


def total_if_total_row_pivoted(conn: sqlite3.Connection) -> int:
    """Pivoting a grand-total row in doubles the total: $162,000.

    Demonstrated arithmetically: the $81,000 total, counted once
    as the sum of the cells and once as its own row.
    """
    grand = conn.execute("SELECT SUM(amount) FROM orders").fetchone()[0]
    cells = sum(j + f + m for _, j, f, m in pivot_monthly(conn))
    return cells + grand
