"""Problem 5 — Durations that survive DST
=====================================

THE PROBLEM (beginner foothold first)
------------------------------------
How long between 00:30 and 02:30 on fall-back Sunday? The wall clock
says two hours. The truth is three — the 1:00–2:00 AM hour happened
twice. Subtracting naive local datetimes gives you the wall-clock lie;
subtracting AWARE datetimes gives you the real elapsed seconds, because
the zone offsets ride along in the arithmetic.

The fix is rung order: parse (problem 1) -> stamp aware (problem 2) ->
subtract. ``(end - start).total_seconds()`` on two aware datetimes is
DST-proof by construction.

Plain words: let the offsets do the math; never subtract wall clocks.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - SLAs and billing measured on naive local time under-bill by an
    hour every spring and over-bill every fall. Auditors notice.
  - Spring-forward (Mar 8, 2026): 2:00–3:00 AM never happens. Wall
    clock says 1:30 -> 3:30 is two hours; the truth is one.
  - ``timedelta`` from aware subtraction is exact even when the two
    endpoints sit in different offsets (-05:00 and -06:00). That mixed
    offset IS the DST transition, handled.

Your solution: ``elapsed_seconds(start_iso, end_iso)`` — parse both ISO
strings (offsets required for the math to be meaningful) and return the
real elapsed seconds as a float.

Plain words: the stopwatch that can't be fooled by the clock changing.

ANALOGY
-------
A stopwatch vs. glancing at the wall clock: the stopwatch measures what
happened; the wall clock measures what the room claims.

YOUR TASK
---------
Implement ``elapsed_seconds`` below. Then run the tests:
``python -m pytest tests -q`` from the day-08 folder.
"""

from problem_01_parse_iso import parse_timestamp


def elapsed_seconds(start_iso, end_iso):
    """Real elapsed seconds between two ISO timestamps (DST-proof)."""
    start = parse_timestamp(start_iso)
    end = parse_timestamp(end_iso)
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("both timestamps must carry a timezone offset")
    return (end - start).total_seconds()


if __name__ == "__main__":
    # fall-back 2026-11-01: wall clock says 2h, the truth is 3h
    print(elapsed_seconds("2026-11-01T00:30:00-05:00",
                          "2026-11-01T02:30:00-06:00"))  # 10800.0
    # spring-forward 2026-03-08: wall clock says 2h, the truth is 1h
    print(elapsed_seconds("2026-03-08T01:30:00-06:00",
                          "2026-03-08T03:30:00-05:00"))  # 3600.0
