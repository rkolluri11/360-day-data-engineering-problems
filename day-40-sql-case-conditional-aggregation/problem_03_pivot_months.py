"""Day 40, problem 3: the pivot without PIVOT.

One row, three months: SUM(CASE WHEN strftime('%m', order_date)='01'
THEN amount ELSE 0 END) AS jan, same for Feb and Mar — $35,000,
$37,000, $9,000. Add GROUP BY region and the same query pivots East
(20000/25000/9000) against West (15000/12000/0). No PIVOT keyword,
no spreadsheet, no second query per month.
"""

from __future__ import annotations

import sqlite3

MONTH_CASES = """SUM(CASE WHEN strftime('%m', order_date) = '01' THEN amount ELSE 0 END),
    SUM(CASE WHEN strftime('%m', order_date) = '02' THEN amount ELSE 0 END),
    SUM(CASE WHEN strftime('%m', order_date) = '03' THEN amount ELSE 0 END)"""


def monthly_totals(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """(Jan, Feb, Mar) totals in one row: (35000, 37000, 9000)."""
    row = conn.execute(f"SELECT {MONTH_CASES} FROM orders").fetchone()
    return (row[0], row[1], row[2])


def pivot_by_region(conn: sqlite3.Connection) -> dict[str, tuple[int, int, int]]:
    """(Jan, Feb, Mar) per region: East (20000, 25000, 9000), West (15000, 12000, 0)."""
    rows = conn.execute(
        f"SELECT region, {MONTH_CASES} FROM orders GROUP BY region"
    ).fetchall()
    return {region: (jan, feb, mar) for region, jan, feb, mar in rows}


def pivot_total(conn: sqlite3.Connection) -> int:
    """The pivot must still account for every dollar: $81,000."""
    jan, feb, mar = monthly_totals(conn)
    return jan + feb + mar
