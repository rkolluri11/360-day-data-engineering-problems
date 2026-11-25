"""Day 48, problem 1: full rebuild - DELETE + INSERT SELECT.

The honest baseline. A full rebuild throws the mart away and
re-derives it from the whole event stream: DELETE FROM
mart_daily_sales, then INSERT SELECT grouped by DATE(event_ts)
and seller. It is always correct - 10 rows, $102,000 - and always
expensive: every load re-reads every event. Everything in this
day is measured against this number. The grouped shape is the
mart's contract: one row per (sale_date, seller), total is the
sum of that day's amounts for that seller.
"""

from __future__ import annotations

import sqlite3


def grouped_by_day(where: str = "") -> str:
    """The mart's defining query: one row per (sale_date, seller)."""
    return (
        "SELECT DATE(event_ts) AS sale_date, seller, SUM(amount) AS total "
        f"FROM order_events {where} GROUP BY DATE(event_ts), seller"
    )


def full_rebuild(conn: sqlite3.Connection) -> None:
    """Wipe the mart and re-derive it from all 10 events."""
    conn.execute("DELETE FROM mart_daily_sales")
    conn.execute(f"INSERT INTO mart_daily_sales {grouped_by_day()}")
    conn.commit()


def mart_rows(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Every mart row, ordered by date then seller."""
    rows = conn.execute(
        "SELECT sale_date, seller, total FROM mart_daily_sales "
        "ORDER BY sale_date, seller"
    ).fetchall()
    return [tuple(r) for r in rows]


def mart_row_count(conn: sqlite3.Connection) -> int:
    """Rows in the mart: 10 after a full rebuild."""
    return conn.execute("SELECT COUNT(*) FROM mart_daily_sales").fetchone()[0]


def mart_total(conn: sqlite3.Connection) -> int:
    """Total dollars in the mart: $102,000 after a full rebuild."""
    return conn.execute("SELECT SUM(total) FROM mart_daily_sales").fetchone()[0]


def source_total(conn: sqlite3.Connection) -> int:
    """Total dollars in the event stream itself: $102,000."""
    return conn.execute("SELECT SUM(amount) FROM order_events").fetchone()[0]
