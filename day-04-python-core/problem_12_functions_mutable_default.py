"""Problem 12 — The audit log that remembered everything, forever
=============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You write a step that collects bad rows:

    def quarantine(row, bad_rows=[]):
        bad_rows.append(row)
        return bad_rows

First batch: 3 bad rows. Second batch: 8 bad rows — wait, 8? The
second batch only had 5 bad rows! The list from the first call was
still there. Python evaluates the default ``[]`` ONCE, when the
``def`` runs, not on every call. Every call shares the same list.

Plain words: the default list is a whiteboard bolted to the wall of
the function. Every call walks into the same room and writes on the
same whiteboard — yesterday's notes are still there.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A long-running ingestion worker processes one file per minute and
calls ``ingest(path, audit=[])`` to record per-file warnings. Because
of the shared default list:

1. File #2's audit report contains file #1's warnings. By file #500
   the "per-file" report holds half a million stale entries.
2. The worker's memory grows all weekend until the container is
   OOM-killed at 3 AM — a slow leak with no single bad line to blame.
3. A retry of a failed file *appends its warnings twice*, so the
   on-call engineer chases phantom duplicates that aren't real.

Your solution: ``ingest(path, audit=None)`` — the None-sentinel
pattern. The function creates a fresh list inside the body on every
call, so each file gets its own audit trail, retries stay idempotent,
and memory stays flat no matter how long the worker runs.

Plain words: instead of a shared whiteboard, each call gets a fresh
sheet of paper. Nobody ever reads yesterday's sheet by accident, and
the room never fills up with old paper.

ANALOGY
-------
A hotel notepad vs. a personal notebook. The hotel notepad stays in
the room — the next guest sees your notes. Your own notebook starts
blank every trip. Default ``[]`` is the hotel notepad; ``None`` plus
a fresh list inside is bringing your own notebook.
"""

from __future__ import annotations


def ingest(path, audit=None):
    """Ingest one file, returning (rows, audit) with a per-call trail.

    ``audit`` uses the None-sentinel: pass your own list to accumulate
    across files deliberately, or omit it for a fresh per-file trail.
    """
    if audit is None:
        audit = []  # fresh sheet of paper, every single call

    rows = _read_file(path)
    for row in rows:
        if not _looks_valid(row):
            # Plain words: note the problem on THIS call's sheet only.
            audit.append({"file": path, "row": row, "reason": "invalid"})
    return rows, audit


def _read_file(path):
    """Stand-in for real file reading (kept tiny for the example)."""
    demo = {
        "2026-10-06-a.csv": [{"id": 1}, {"id": None}, {"id": 3}],
        "2026-10-06-b.csv": [{"id": 4}, {"id": 5}],
    }
    return demo.get(path, [])


def _looks_valid(row):
    """A row is valid when it has a non-null id."""
    return row.get("id") is not None


def quarantine(row, bad_rows=None):
    """Collect one bad row; never share state between callers.

    The textbook trap, fixed: the default is None, and the list is
    born inside the call.
    """
    if bad_rows is None:
        bad_rows = []
    bad_rows.append(row)
    return bad_rows


if __name__ == "__main__":
    # Each file gets its own audit trail — no leakage between calls.
    _, audit_a = ingest("2026-10-06-a.csv")
    _, audit_b = ingest("2026-10-06-b.csv")
    print("file A warnings:", len(audit_a))  # 1
    print("file B warnings:", len(audit_b))  # 0 (not 1!)

    # Retry is idempotent: re-running a file doesn't double-append.
    _, audit_retry = ingest("2026-10-06-a.csv")
    print("retry warnings:", len(audit_retry))  # still 1

    # Deliberate accumulation still possible when YOU ask for it.
    shared = []
    quarantine({"id": 9}, shared)
    quarantine({"id": 10}, shared)
    print("explicit shared list:", len(shared))  # 2 — your choice
    print("fresh call:", len(quarantine({"id": 11})))  # 1 — isolated
