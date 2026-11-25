"""Day 48, problem 2: the watermark - MAX(event_ts) of the last load.

An incremental load cannot ask "what is new?" without remembering
where the last load stopped. The watermark is that memory: one row
in load_state, model = 'daily_sales', watermark = the latest
event_ts the load saw. Load 1 takes everything that arrived by
'2026-02-12 18:00' - 6 events, $72,000 - and its watermark is
MAX(event_ts) over those rows: '2026-02-12 13:30', Irene's
Feb 12 order. The watermark is written in the SAME transaction
as the mart rows, so it advances only on success: if the insert
fails, the watermark stays where it was and the next run retries
the same window instead of skipping it.
"""

from __future__ import annotations

import sqlite3

from problem_01_full_rebuild import grouped_by_day

MODEL = "daily_sales"
LOAD1_CUTOFF = "2026-02-12 18:00"


def load_1(conn: sqlite3.Connection) -> None:
    """Load everything arrived by the cutoff, then record the watermark.

    Mart rows and watermark are one transaction: the watermark
    advances only if the insert commits.
    """
    conn.execute(
        f"INSERT INTO mart_daily_sales {grouped_by_day('WHERE arrived_at <= ?')}",
        (LOAD1_CUTOFF,),
    )
    conn.execute(
        "INSERT INTO load_state (model, watermark) VALUES (?, ?) "
        "ON CONFLICT(model) DO UPDATE SET watermark = excluded.watermark",
        (MODEL, load_1_watermark(conn)),
    )
    conn.commit()


def load_1_watermark(conn: sqlite3.Connection) -> str:
    """MAX(event_ts) over load 1's rows: '2026-02-12 13:30'."""
    return conn.execute(
        "SELECT MAX(event_ts) FROM order_events WHERE arrived_at <= ?",
        (LOAD1_CUTOFF,),
    ).fetchone()[0]


def watermark(conn: sqlite3.Connection) -> str | None:
    """The stored watermark, or None before the first successful load."""
    row = conn.execute(
        "SELECT watermark FROM load_state WHERE model = ?", (MODEL,)
    ).fetchone()
    return row[0] if row else None


def load_1_event_count(conn: sqlite3.Connection) -> int:
    """Events load 1 sees: 6."""
    return conn.execute(
        "SELECT COUNT(*) FROM order_events WHERE arrived_at <= ?",
        (LOAD1_CUTOFF,),
    ).fetchone()[0]


def load_1_total(conn: sqlite3.Connection) -> int:
    """Dollars load 1 sees: $72,000."""
    return conn.execute(
        "SELECT SUM(amount) FROM order_events WHERE arrived_at <= ?",
        (LOAD1_CUTOFF,),
    ).fetchone()[0]
