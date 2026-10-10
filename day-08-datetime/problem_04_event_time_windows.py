"""Problem 4 — Event-time vs processing-time windows
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Every event carries TWO clocks: ``event_time`` (when it happened) and
``processed_at`` (when your job saw it). The first-draft version windows
by ``processed_at`` — simple, and wrong the moment anything arrives
late. A phone that was offline for three hours dumps its events at 2 PM;
they belong to the 11 AM window, not the 2 PM one.

The fix: window on ``event_time``. Truncate it to the window start —
``event_time.replace(minute=0, second=0, microsecond=0)`` for hourly
windows — and group. ``processed_at`` stays in the payload for ops
(retry dashboards, lag alerts), but it never decides the bucket.

Plain words: the row's clock beats your job's clock.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Late data is NORMAL: backfills, retries, and offline devices all
    arrive after their window "closed". Event-time windows absorb them;
    processing-time windows silently misattribute them.
  - ``replace(minute=0)`` on an aware datetime keeps the zone — the
    window start stays comparable with other aware stamps.
  - Windowing on naive datetimes from mixed zones merges different
    real hours into one bucket. Aware in, aware out (rungs 2–3).

Your solution: ``assign_windows(events, window_hours=1)`` — ``events``
are dicts with an aware ``"event_time"``; return
``{window_start_utc_datetime: [events]}``. Window starts are UTC.

Plain words: every event lands in the window where it happened.

ANALOGY
-------
Postmark vs. delivery day: the letter counts for the day it was mailed,
not the day the truck finally showed up.

YOUR TASK
---------
Implement ``assign_windows`` below. Then run the tests:
``python -m pytest tests -q`` from the day-08 folder.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone


def assign_windows(events, window_hours=1):
    """Group events by event_time window; window starts returned in UTC."""
    step = timedelta(hours=window_hours).total_seconds()
    windows = defaultdict(list)
    for e in events:
        et = e["event_time"]
        epoch = et.timestamp()
        start = datetime.fromtimestamp(epoch - (epoch % step), tz=timezone.utc)
        windows[start].append(e)
    return dict(windows)


if __name__ == "__main__":
    from zoneinfo import ZoneInfo
    chicago = ZoneInfo("America/Chicago")
    events = [
        {"id": 1, "event_time": datetime(2026, 10, 11, 9, 15, tzinfo=chicago),
         "processed_at": datetime(2026, 10, 11, 9, 16, tzinfo=chicago)},
        {"id": 2, "event_time": datetime(2026, 10, 11, 9, 45, tzinfo=chicago),
         "processed_at": datetime(2026, 10, 11, 12, 5, tzinfo=chicago)},  # 3h late
        {"id": 3, "event_time": datetime(2026, 10, 11, 10, 5, tzinfo=chicago),
         "processed_at": datetime(2026, 10, 11, 10, 6, tzinfo=chicago)},
    ]
    for start, evts in sorted(assign_windows(events).items()):
        print(start, "->", [e["id"] for e in evts])
    # the late event (id 2) keeps its 9 AM window, not the noon one
