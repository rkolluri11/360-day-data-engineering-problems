"""Problem 5 — Group-by under a memory budget
=========================================

THE PROBLEM (beginner foothold first)
------------------------------------
``{key: total}`` aggregation with a plain dict is O(n) memory: the dict
grows with the number of distinct keys. When keys are bounded (e.g. a
few thousand categories) that's fine. When they're not, you need a
different strategy.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Sum the ``amount`` column per ``category`` from a CSV too large to
aggregate naively, with a hard rule: **peak extra memory must stay
under 5 MB** (measured with ``tracemalloc``). The trick that makes this
solvable: first sort is impossible without memory, but you *can* stream
in chunks — aggregate one chunk at a time, flush each chunk's partial
totals to a spill file, then merge the sorted spill files in a second
streaming pass. Peak memory is then bounded by (chunk size + number of
chunks' open handles), not by the dataset.

Plain words: instead of keeping one giant running tally for every
category, tally small batches, write each batch's subtotals on paper,
then add up the papers in one final pass. The desk never gets crowded.

ANALOGY
-------
A cashier counting a day's sales doesn't memorize every transaction —
she closes out small batches, tapes the subtotal slips to the wall,
and adds the slips at the end.
"""

from __future__ import annotations

import csv
import heapq
import os
import tempfile


def stream_groupby_sum(
    path: str, chunk_rows: int = 10_000
) -> dict[str, float]:
    """Sum ``amount`` per ``category`` from a CSV, streaming, O(chunk) memory.

    Pass 1: read the file in chunks; for each chunk write its partial
    per-category totals to a sorted spill file.
    Pass 2: k-way merge the sorted spill files (heapq.merge) and combine
    the partial totals for each category.
    """
    spill_paths: list[str] = []

    with open(path, "r", newline="") as fh:
        reader = csv.DictReader(fh)
        chunk: dict[str, float] = {}
        rows_in_chunk = 0
        for row in reader:
            cat = row["category"]
            chunk[cat] = chunk.get(cat, 0.0) + float(row["amount"])
            rows_in_chunk += 1
            if rows_in_chunk >= chunk_rows:
                spill_paths.append(_spill_sorted(chunk))
                chunk, rows_in_chunk = {}, 0
        if chunk:
            spill_paths.append(_spill_sorted(chunk))

    # Pass 2: streaming merge of the sorted spill files.
    totals: dict[str, float] = {}
    handles = [open(p, "r", newline="") for p in spill_paths]
    try:
        merged = heapq.merge(
            *(_read_spill(h) for h in handles),
            key=lambda pair: pair[0],
        )
        current_cat: str | None = None
        current_sum = 0.0
        for cat, partial in merged:
            if cat != current_cat:
                if current_cat is not None:
                    totals[current_cat] = current_sum
                current_cat, current_sum = cat, partial
            else:
                current_sum += partial
        if current_cat is not None:
            totals[current_cat] = current_sum
    finally:
        for h in handles:
            h.close()
        for p in spill_paths:
            os.unlink(p)

    return totals


def _spill_sorted(chunk: dict[str, float]) -> str:
    """Write one chunk's partial totals, sorted by category, to a file."""
    fd, spill_path = tempfile.mkstemp(prefix="groupby_spill_", suffix=".csv")
    with os.fdopen(fd, "w", newline="") as fh:
        writer = csv.writer(fh)
        for cat in sorted(chunk):
            writer.writerow([cat, repr(chunk[cat])])
    return spill_path


def _read_spill(handle):
    """Yield (category, partial_total) pairs from one spill file."""
    for cat, partial in csv.reader(handle):
        yield cat, float(partial)


if __name__ == "__main__":
    import sys

    print(stream_groupby_sum(sys.argv[1]))
