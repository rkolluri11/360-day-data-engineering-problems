"""Problem 5 — 10M rows, flat memory: streaming aggregation
============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
The classic batch shape:

    rows = load_all("events.jsonl")          # 10M dicts in RAM
    totals = {}
    for r in rows:
        totals[r["user"]] = totals.get(r["user"], 0) + r["amt"]

Peak memory = the whole file + the totals. The Day 1 OOMKill came
from exactly this.

The streaming rewrite holds one row at a time:

    totals = {}
    for line in open("events.jsonl"):        # one line in memory
        r = json.loads(line)
        totals[r["user"]] = totals.get(r["user"], 0) + r["amt"]

Peak memory = one row + one dict of *distinct keys*. If the file has
10M rows but 50k users, you hold 50k entries — never 10M.

Plain words: count the crowd by tally marks on a clipboard, not by
photographing every face.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Streaming aggregation has its own traps:

  - **Unbounded key space:** per-user totals are fine at 50k users;
    per-session-id totals on a bot flood is a memory leak wearing a
    dict. Bound it: top-K with a heap, or windowed aggregation.
  - **Late/out-of-order data:** a streaming sum over event time needs
    watermarks; without them, one late row rewrites history. Know
    whether your totals are append-only or revisable.
  - **Poison rows mid-stream:** ``json.loads`` on line 9,999,999
    throws — after 9,999,998 rows already tallied. Catch per-row,
    count the skips, and keep the offset so the rerun resumes, not
    restarts.
  - ``itertools.groupby`` only groups *consecutive* equal keys — feed
    it unsorted data and you get one group per run, not per key. For
    sorted streams it's O(1) memory; for unsorted streams, sort
    first or use the dict.

Your solution: ``streaming_group_sum(row_gen, key, value)`` — consumes
a generator of dicts, returns ``(totals, rows_seen, skipped)`` where
totals maps each distinct key to the sum of float(value). Skips rows
with missing/unparseable keys or values. Must stream: the test feeds
it a generator with a pull counter and asserts the source was never
materialized (no ``list()`` on it — verified by a 1M-row source that
would blow the test's memory budget if loaded).

Plain words: the clipboard never becomes a filing cabinet.

ANALOGY
-------
Election night tally boards: each precinct phones in one number, the
board updates one cell. Nobody ships every ballot to the studio.

YOUR TASK
---------
Implement ``streaming_group_sum`` below. Then run the tests:
``python -m pytest tests -q`` from the day-06 folder.
"""


def streaming_group_sum(row_gen, key, value):
    """Aggregate float(value) per distinct key over generator *row_gen*.

    Streams: holds one row at a time plus the per-key totals dict.
    Returns (totals, rows_seen, skipped).
    """
    totals = {}
    rows_seen = 0
    skipped = 0
    for row in row_gen:
        rows_seen += 1
        try:
            k = row[key]
            v = float(row[value])
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if k is None:
            skipped += 1
            continue
        totals[k] = totals.get(k, 0.0) + v
    return totals, rows_seen, skipped


def top_k(totals, k):
    """Return the top-k (key, total) pairs by total, descending."""
    import heapq

    return heapq.nlargest(k, totals.items(), key=lambda kv: kv[1])


if __name__ == "__main__":
    # A "10M-row file" that never exists in memory:
    def fake_events(n):
        for i in range(n):
            yield {"user": f"u{i % 50_000}", "amt": str(i % 100)}

    totals, seen, skipped = streaming_group_sum(fake_events(10_000_000), "user", "amt")
    print("rows:", seen, "skipped:", skipped, "distinct users:", len(totals))
    print("top 3:", top_k(totals, 3))
