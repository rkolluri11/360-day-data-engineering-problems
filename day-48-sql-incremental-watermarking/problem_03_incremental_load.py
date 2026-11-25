"""Day 48, problem 3: incremental load - WHERE event_ts > watermark.

Load 2 reads only what is new: events with event_ts strictly
greater than the watermark, arrived by '2026-02-18 18:00'. That
is 3 events, $26,000 - Feb 14 Frank $9,000, Feb 16 David $11,000,
Feb 18 Irene $6,000 - and the mart grows to 9 rows, $98,000.

The strict > is the whole point. Event 6 happened AT the
watermark ('2026-02-12 13:30'): load 1 already counted it, so
load 2 must not. A >= would reprocess it - and with the mart's
(sale_date, seller) primary key the second insert would either
fail or, with INSERT OR REPLACE, silently rewrite a correct row.
The boundary event is NOT reprocessed: after loads 1+2 there is
exactly one ('2026-02-12', 'Irene Novak') row, $7,000.

Note the watermark does NOT move here. This naive load inserts
the new rows and leaves the watermark at load 1's value - the
lookback fix in problem 5 is what moves it on.
"""

from __future__ import annotations

import sqlite3

from problem_01_full_rebuild import grouped_by_day
from problem_02_watermark import LOAD1_CUTOFF, MODEL, watermark

LOAD2_CUTOFF = "2026-02-18 18:00"


def incremental_load(conn: sqlite3.Connection) -> int:
    """Insert grouped rows for events after the watermark. Returns rows inserted."""
    wm = watermark(conn)
    if wm is None:
        raise ValueError("no watermark: run load 1 first")
    cur = conn.execute(
        f"INSERT INTO mart_daily_sales {grouped_by_day('WHERE event_ts > ? AND arrived_at <= ?')}",
        (wm, LOAD2_CUTOFF),
    )
    conn.commit()
    return cur.rowcount


def incremental_event_count(conn: sqlite3.Connection) -> int:
    """Events load 2 sees: 3."""
    wm = watermark(conn)
    return conn.execute(
        "SELECT COUNT(*) FROM order_events "
        "WHERE event_ts > ? AND arrived_at <= ?",
        (wm, LOAD2_CUTOFF),
    ).fetchone()[0]


def incremental_total(conn: sqlite3.Connection) -> int:
    """Dollars load 2 sees: $26,000."""
    wm = watermark(conn)
    return conn.execute(
        "SELECT SUM(amount) FROM order_events "
        "WHERE event_ts > ? AND arrived_at <= ?",
        (wm, LOAD2_CUTOFF),
    ).fetchone()[0]


def boundary_row_count(conn: sqlite3.Connection) -> int:
    """Mart rows for event 6's day and seller: exactly 1 - not reprocessed."""
    return conn.execute(
        "SELECT COUNT(*) FROM mart_daily_sales "
        "WHERE sale_date = '2026-02-12' AND seller = 'Irene Novak'"
    ).fetchone()[0]


def mart_total_after_load_2(conn: sqlite3.Connection) -> int:
    """Mart total after loads 1+2: $98,000 - $4,000 short of the source."""
    return conn.execute("SELECT SUM(total) FROM mart_daily_sales").fetchone()[0]
