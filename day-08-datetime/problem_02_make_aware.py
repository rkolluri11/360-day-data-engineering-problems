"""Problem 2 — Naive is a trap: go aware
=====================================

THE PROBLEM (beginner foothold first)
------------------------------------
``parse_timestamp("2026-10-11T09:00:00")`` hands you a NAIVE datetime —
no timezone attached. Whose 9 AM? Python does not know, and it will not
warn you: subtracting two naive datetimes from different zones gives you
a confident, wrong answer.

The fix is one stamp: ``dt.replace(tzinfo=ZoneInfo("America/Chicago"))``.
``replace`` does not convert — it DECLARES what the wall-clock reading
meant. Then ``astimezone(timezone.utc)`` converts for real. Read it as:
stamp the meaning, then convert the moment.

Plain words: a timestamp without a zone is a price without a currency.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``replace(tzinfo=...)`` on an already-aware datetime SILENTLY
    overwrites the real zone. Guard with ``dt.tzinfo is None``.
  - The DST fold: on fall-back Sunday the local 1:30 AM happens twice.
    ``replace`` picks ``fold=0`` (the first occurrence) by default —
    fine for bucketing, dangerous for exactly-once billing.
  - Comparing naive and aware raises ``TypeError`` — Python's ONLY
    warning about zones. Everything else lies quietly.

Your solution: ``to_utc(dt, tz_name)`` — if ``dt`` is naive, stamp it
with ``tz_name``; then return it converted to UTC. Raise ``TypeError``
for non-datetime input.

Plain words: stamp the meaning once, then speak UTC everywhere.

ANALOGY
-------
Declaring the currency before converting it: you cannot convert dollars
to euros until someone tells you the price was in dollars.

YOUR TASK
---------
Implement ``to_utc`` below. Then run the tests:
``python -m pytest tests -q`` from the day-08 folder.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def to_utc(dt, tz_name):
    """Stamp a naive datetime with tz_name, then convert to UTC."""
    if not isinstance(dt, datetime):
        raise TypeError("expected a datetime, got %r" % (dt,))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))  # stamp, don't convert
    return dt.astimezone(timezone.utc)


if __name__ == "__main__":
    # 9 AM Chicago (CDT, UTC-5) -> 2 PM UTC
    print(to_utc(datetime(2026, 10, 11, 9, 0), "America/Chicago"))
    # already aware: stamped zone is respected, not overwritten
    aware = datetime(2026, 10, 11, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    print(to_utc(aware, "America/Chicago"))  # 03:30 UTC
