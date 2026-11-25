"""Day 48, problem 5: lookback fix - reprocess a window, then move on.

Late data cannot be caught by event_ts > watermark, so the fix
reprocesses a window instead of only the new rows. With a 3-day
lookback, load 2 re-derives everything after
datetime(watermark, '-3 days') = '2026-02-09 13:30': 6 events,
$42,000 - events 5, 6, 7, 8, 9, 10, including the late event 9.
The mart window is deleted first (sale_date >= '2026-02-09',
the DATE of the lookback cutoff) and the window is re-inserted
grouped, so the mart ends at 10 rows, $102,000 - matching the
full rebuild. Deleting before inserting is what makes the load
idempotent: run the window twice and the mart is identical,
because the same rows are removed and rebuilt each time. Only
then does the watermark advance, to MAX(event_ts) over arrived
rows: '2026-02-18 15:45'.
"""

from __future__ import annotations

import sqlite3

from problem_01_full_rebuild import grouped_by_day
from problem_02_watermark import MODEL, watermark
from problem_03_incremental_load import LOAD2_CUTOFF

LOOKBACK_DAYS = 3


def lookback_cutoff(conn: sqlite3.Connection) -> str:
    """datetime(watermark, '-3 days'): '2026-02-09 13:30:00'."""
    wm = watermark(conn)
    return conn.execute(
        "SELECT datetime(?, ?)", (wm, f"-{LOOKBACK_DAYS} days")
    ).fetchone()[0]


def lookback_window_start(conn: sqlite3.Connection) -> str:
    """DATE of the lookback cutoff: '2026-02-09' - the mart delete boundary."""
    return conn.execute(
        "SELECT DATE(datetime(?, ?))", (watermark(conn), f"-{LOOKBACK_DAYS} days")
    ).fetchone()[0]


def lookback_event_count(conn: sqlite3.Connection) -> int:
    """Events inside the lookback window: 6."""
    return conn.execute(
        "SELECT COUNT(*) FROM order_events "
        "WHERE event_ts > datetime(?, ?) AND arrived_at <= ?",
        (watermark(conn), f"-{LOOKBACK_DAYS} days", LOAD2_CUTOFF),
    ).fetchone()[0]


def lookback_total(conn: sqlite3.Connection) -> int:
    """Dollars inside the lookback window: $42,000."""
    return conn.execute(
        "SELECT SUM(amount) FROM order_events "
        "WHERE event_ts > datetime(?, ?) AND arrived_at <= ?",
        (watermark(conn), f"-{LOOKBACK_DAYS} days", LOAD2_CUTOFF),
    ).fetchone()[0]


def lookback_load(conn: sqlite3.Connection) -> None:
    """Delete the mart window, re-insert it grouped, advance the watermark.

    One transaction: the watermark moves only if the rebuild commits.
    """
    wm = watermark(conn)
    cutoff = f"-{LOOKBACK_DAYS} days"
    conn.execute(
        "DELETE FROM mart_daily_sales WHERE sale_date >= DATE(datetime(?, ?))",
        (wm, cutoff),
    )
    conn.execute(
        f"INSERT INTO mart_daily_sales {grouped_by_day('WHERE event_ts > datetime(?, ?) AND arrived_at <= ?')}",
        (wm, cutoff, LOAD2_CUTOFF),
    )
    new_watermark = conn.execute(
        "SELECT MAX(event_ts) FROM order_events WHERE arrived_at <= ?",
        (LOAD2_CUTOFF,),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO load_state (model, watermark) VALUES (?, ?) "
        "ON CONFLICT(model) DO UPDATE SET watermark = excluded.watermark",
        (MODEL, new_watermark),
    )
    conn.commit()
