"""Problem 18 — The silent zip that shipped misaligned rows
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Three parallel lists describe the same sensor readings:

    times   = ["10:00", "10:01", "10:02"]
    values  = [21.5, 21.7, 21.6]
    sensors = ["s1", "s1", "s1"]

The beginner walks them with an index:

    rows = []
    for i in range(len(times)):
        rows.append((times[i], sensors[i], values[i]))

Plain words: three columns of a spreadsheet stored as three
separate lists; you stitch row *i* from column *i* of each. But
``range(len(...))`` only names ONE list's length — and ``zip``
quietly stops at the SHORTEST list, so a ragged feed loses rows
without a sound.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Three upstream systems emit one array each per 5-minute window:
``timestamps`` (ingest service), ``readings`` (meter API), ``units``
(config service). One night the meter API drops a single reading —
499 values for 500 timestamps. The merge code used a plain ``zip``:

    for ts, val, unit in zip(timestamps, readings, units):
        write(ts, val, unit)

``zip`` stopped at 499. Nobody was told. 500 timestamps went in,
499 rows came out, and the missing row was the one carrying the
overnight peak — the exact row the billing reconciliation needed.
The dashboard showed "all windows complete" because nothing raised.

Your solution: ``merge_feeds(timestamps, readings, units)`` —
``zip(..., strict=True)`` so a length mismatch RAISES instead of
truncating, plus ``enumerate`` so the error (and every log line)
carries the real row number, not a mystery offset:

    [{"row": i, "ts": ts, "reading": v, "unit": u}
     for i, (ts, v, u) in enumerate(zip(timestamps, readings, units,
                                        strict=True))]

Plain words: zip with strict=True is a bouncer that counts heads —
if the three lines don't have the same number of people, nobody
gets in and you hear about it immediately. Enumerate is the
numbered wristband so you can point at exactly which row failed.

ANALOGY
-------
Zipping a jacket where one side has fewer teeth: a normal zip just
stops where the teeth run out and looks closed. strict=True is the
jacket that refuses to close and tells you a tooth is missing.
"""

from __future__ import annotations


# --- BEFORE: index-walking + silent zip -----------------------------------
# Plain words: works when all three lists agree, and fails SILENTLY
# the one night they don't — the most dangerous kind of bug.

def merge_feeds_loose(timestamps, readings, units):
    """Merge parallel feeds; silently drops rows on length mismatch."""
    rows = []
    for i in range(len(timestamps)):
        rows.append({"row": i, "ts": timestamps[i],
                     "reading": readings[i], "unit": units[i]})
    return rows  # IndexError if readings is short; silent loss with zip()


# --- AFTER: strict zip + enumerate ----------------------------------------
# Plain words: strict=True turns a silent data-loss bug into a loud,
# catchable error at the exact row where the feeds disagree.

def merge_feeds(timestamps, readings, units):
    """Merge three aligned feeds into row dicts.

    Raises ValueError if the feeds have different lengths — a short
    feed is a data-quality incident, never something to truncate.
    Row numbers come from enumerate, starting at 0.
    """
    try:
        pairs = zip(timestamps, readings, units, strict=True)
    except TypeError as exc:  # very old Python without strict=
        raise ValueError(
            "feeds have mismatched lengths (strict zip unavailable)"
        ) from exc
    try:
        return [
            {"row": i, "ts": ts, "reading": value, "unit": unit}
            for i, (ts, value, unit) in enumerate(pairs)
        ]
    except ValueError as exc:
        raise ValueError(
            f"feed length mismatch: {exc} — refusing to ship misaligned rows"
        ) from exc


if __name__ == "__main__":
    ts = ["10:00", "10:01", "10:02"]
    vals = [21.5, 21.7, 21.6]
    units = ["C", "C", "C"]
    print(merge_feeds(ts, vals, units))
    # [{'row': 0, ...}, {'row': 1, ...}, {'row': 2, ...}]

    try:
        merge_feeds(ts, vals[:2], units)  # meter API dropped a reading
    except ValueError as e:
        print("CAUGHT:", e)  # loud failure, no silent truncation
