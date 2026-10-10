"""Problem 3 — Bucket on local date, not UTC date
=================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A "daily" report needs every event in the bucket of ITS local date.
Events are stored in UTC (rung 4 of the ladder). The naive version takes
``stamp.date()`` straight off the UTC datetime — and every event between
midnight and 5 AM Chicago time lands on the WRONG day.

The fix: convert FIRST, bucket SECOND —
``stamp.astimezone(local).date()``. One line, and the bucket is the date
the customer actually experienced.

Plain words: the date is a display question; answer it in display time.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - DST fall-back (Nov 1, 2026): the 1:00–2:00 AM hour happens TWICE.
    UTC-based bucketing is immune — both occurrences convert to the
    same local date. Wall-clock-string bucketing is not.
  - ``Counter`` over converted dates is O(n) and exact — no seen-list,
    no sorting, no second pass (see Day 7, rung 3).
  - Never bucket on the raw string's date part: "2026-11-01T00:30:00Z"
    says Nov 1, but in Chicago it is still Oct 31.

Your solution: ``bucket_by_local_date(stamps, tz_name)`` — ``stamps``
is a list of AWARE datetimes; return ``{date: count}`` keyed by the
date in ``tz_name``.

Plain words: convert to local, then ask "what day was it there?".

ANALOGY
-------
Sorting mail by the recipient's calendar, not the postmark's: the stamp
says when it was sent; the bucket says which day they lived it.

YOUR TASK
---------
Implement ``bucket_by_local_date`` below. Then run the tests:
``python -m pytest tests -q`` from the day-08 folder.
"""

from collections import Counter
from zoneinfo import ZoneInfo


def bucket_by_local_date(stamps, tz_name):
    """Count aware datetimes by their calendar date in tz_name."""
    tz = ZoneInfo(tz_name)
    return dict(Counter(s.astimezone(tz).date() for s in stamps))


if __name__ == "__main__":
    from datetime import datetime, timezone
    chicago = "America/Chicago"
    # 00:30 CDT Nov 1, 01:30 CDT Nov 1 (first), 01:30 CST Nov 1 (second)
    stamps = [
        datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 1, 7, 30, tzinfo=timezone.utc),
    ]
    print(bucket_by_local_date(stamps, chicago))  # all Nov 1
    # the UTC-midnight trap: 04:59 UTC Nov 1 is still Oct 31 in Chicago
    print(bucket_by_local_date(
        [datetime(2026, 11, 1, 4, 59, tzinfo=timezone.utc)], chicago))
