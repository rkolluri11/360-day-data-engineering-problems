"""Day 48, problem 4: the late row - the watermark cannot see arrivals.

Event 9 is David's $4,000 order from 2026-02-11 08:00. Its event
time is BEFORE the watermark ('2026-02-12 13:30'), so the naive
predicate event_ts > watermark never selects it. But it ARRIVED
at 2026-02-15 07:30 - after load 1 ran at 18:00 on Feb 12. The
watermark tracks event time, not arrival time, so late data is
invisible to it. After loads 1+2 the mart holds 9 rows, $98,000
while the source holds 10 events, $102,000: the mart is $4,000
short, exactly event 9's amount, and there is no mart row for
('2026-02-11', 'David Kim'). The model is wrong and nothing
errored - that is why a late-data check belongs in every
incremental pipeline.
"""

from __future__ import annotations

import sqlite3

from problem_01_full_rebuild import mart_total, source_total
from problem_02_watermark import LOAD1_CUTOFF, watermark


def late_events(conn: sqlite3.Connection) -> list[int]:
    """Events whose event time is at or before the watermark but which
    arrived after load 1 ran: [9]."""
    wm = watermark(conn)
    rows = conn.execute(
        "SELECT event_id FROM order_events "
        "WHERE event_ts <= ? AND arrived_at > ? ORDER BY event_id",
        (wm, LOAD1_CUTOFF),
    ).fetchall()
    return [r[0] for r in rows]


def event_in_mart(conn: sqlite3.Connection, event_id: int) -> bool:
    """True if a mart row covers this event's (sale_date, seller)."""
    row = conn.execute(
        "SELECT DATE(event_ts), seller FROM order_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    sale_date, seller = row
    return (
        conn.execute(
            "SELECT COUNT(*) FROM mart_daily_sales "
            "WHERE sale_date = ? AND seller = ?",
            (sale_date, seller),
        ).fetchone()[0]
        > 0
    )


def mart_shortfall(conn: sqlite3.Connection) -> int:
    """Source total minus mart total: $4,000 after loads 1+2."""
    return source_total(conn) - mart_total(conn)


def mart_row_count(conn: sqlite3.Connection) -> int:
    """Rows in the mart after loads 1+2: 9, not 10."""
    return conn.execute("SELECT COUNT(*) FROM mart_daily_sales").fetchone()[0]
