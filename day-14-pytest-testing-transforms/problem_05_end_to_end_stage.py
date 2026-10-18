"""Problem 5 — test the whole stage: CSV in, CSV out, tmp_path
=============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Unit tests prove functions; STAGE tests prove the pipeline step. A stage
reads a dirty CSV, cleans it, and writes two files — clean output and
quarantine report. pytest's ``tmp_path`` fixture hands each test a fresh
scratch directory, so the test uses REAL files with zero cleanup:

    def test_stage(tmp_path):
        in_csv = tmp_path / "in.csv"
        in_csv.write_text("order_id,amount,status\\no-1,10.00,paid\\n...")
        stats = run_stage(in_csv, tmp_path / "out.csv", tmp_path / "q.csv")
        assert stats == {"in": 1, "clean": 1, "quarantined": 0}

Plain words: a stage test is a dress rehearsal — full costume (real CSV
files), full lights (a real directory) — so opening night (production)
has no surprises.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The test asserts the FILES, not just the return value: read
    ``out.csv`` back and check the parsed amounts are floats-as-text,
    read the quarantine CSV and check the ``_reason`` column. Return
    values lie; files don't.
  - IDEMPOTENCY: running the stage twice over the same inputs must
    produce byte-identical outputs and identical stats. Stages get
    retried after partial failures — a retry must not double-count.
    (Our stage overwrites its outputs, so re-runs converge.)
  - Stats are the stage's receipt: ``{"in": n, "clean": c,
    "quarantined": q}`` with ``in == clean + quarantined`` — every input
    row is accounted for, none swallowed, none duplicated.
  - Only the stdlib ``csv`` module — no pandas, no fixtures-as-magic:
    the point is the testing PATTERN (tmp_path + file assertions +
    idempotency), portable to any stack.

Your solution: ``run_stage(in_csv, out_csv, quarantine_csv)`` below.
Then run the tests: ``python -m pytest tests -q`` from the day-14 folder.

ANALOGY
-------
An idempotent stage test is rehearsing the fire drill twice: the second
run must look exactly like the first — same headcount at the muster
point, nobody counted twice, nobody left inside.
"""

import csv

from problem_04_quarantine_not_crash import clean_batch

CLEAN_FIELDS = ["order_id", "amount", "status"]
QUARANTINE_FIELDS = ["order_id", "amount", "status", "_reason"]


def run_stage(in_csv, out_csv, quarantine_csv):
    """Run one pipeline stage: dirty CSV in, clean + quarantine CSVs out.

    Returns {"in": n, "clean": c, "quarantined": q} with n == c + q.
    Overwrites outputs, so re-runs are idempotent.
    """
    with open(in_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    clean, quarantined = clean_batch(rows)

    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CLEAN_FIELDS)
        writer.writeheader()
        writer.writerows(clean)

    with open(quarantine_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUARANTINE_FIELDS)
        writer.writeheader()
        for item in quarantined:
            writer.writerow({**item["_row"], "_reason": item["_reason"]})

    return {"in": len(rows), "clean": len(clean), "quarantined": len(quarantined)}
