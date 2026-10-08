"""Problem 20 — The pipeline that needed the file twice in RAM
=========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Sum the squares of the even numbers 0..9. The beginner builds a
list at every stage:

    evens = [x for x in range(10) if x % 2 == 0]   # list 1
    squares = [x * x for x in evens]               # list 2
    total = sum(squares)

Plain words: three buckets — filter into one, transform into
another, then add. A generator expression uses parentheses instead
of brackets and holds NOTHING:

    total = sum(x * x for x in range(10) if x % 2 == 0)

Each value is produced, squared, and added one at a time. The
"list" between stages never exists.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The fraud team needs one number every morning: total USD volume of
settled, non-test transactions from yesterday's 20 GB JSONL export.
The original code chained list-building stages:

    lines   = open(path).read().splitlines()          # 20 GB in RAM!
    parsed  = [json.loads(l) for l in lines]          # +20 GB of dicts
    settled = [t for t in parsed
               if t["status"] == "settled" and not t["is_test"]]
    total   = sum(t["amount_usd"] for t in settled)

The worker had 8 GB of RAM. The job was OOM-killed before it ever
reached ``sum`` — it needed the file in memory two or three times
over just to compute a single number.

Your solution: ``daily_settled_volume(path)`` — a chain of
generator expressions: read line-by-line, parse lazily, filter
lazily, feed straight into ``sum``. Peak memory is ONE line plus
one dict, no matter how big the file is. The same trick powers
``count_distinct_customers``-style helpers that must stream.

One honest gotcha included: generators are SINGLE-USE. Hand the
same generator to two consumers and the second one sees nothing —
the code comments show the safe pattern (re-create, or tee()).

Plain words: instead of photocopying the entire warehouse manifest
three times and then adding up one column, you walk the aisles once
with a clipboard, adding as you go. The clipboard never holds more
than one line.

ANALOGY
-------
A water pipeline vs buckets: the list version fills bucket one from
the reservoir, pours it into bucket two, then drinks from bucket
two. The generator version is a pipe — water flows from reservoir
to your glass with no bucket anywhere, and the pipe works whether
the reservoir is a pond or an ocean.
"""

from __future__ import annotations

import json


# --- BEFORE: buckets at every stage ---------------------------------------
# Plain words: each stage materializes the whole dataset before the
# next stage starts. Memory needed ~ 3x the file. OOM-killed at 8 GB.

def daily_settled_volume_eager(path):
    """Total settled non-test USD volume — loads everything into RAM."""
    with open(path) as f:
        lines = f.read().splitlines()          # the whole file, at once
    parsed = [json.loads(line) for line in lines]      # all dicts, at once
    settled = [t for t in parsed
               if t.get("status") == "settled" and not t.get("is_test")]
    return round(sum(t.get("amount_usd", 0) for t in settled), 2)


# --- AFTER: one pipe, one row in memory at a time --------------------------
# Plain words: parentheses, not brackets. Each stage pulls ONE item
# from the previous stage only when `sum` asks for the next number.

def _settled_amounts(path):
    """Lazily yield USD amounts of settled, non-test transactions."""
    with open(path) as f:
        parsed = (json.loads(line) for line in f)          # one dict at a time
        settled = (t for t in parsed
                   if t.get("status") == "settled"         # filter, lazily
                   and not t.get("is_test"))
        for t in settled:
            yield t.get("amount_usd", 0)


def daily_settled_volume(path):
    """Total settled non-test USD volume, streaming.

    Peak memory is a single line + a single dict, regardless of
    file size. Safe for files far larger than RAM.
    """
    return round(sum(_settled_amounts(path)), 2)


def count_large_settled(path, threshold_usd=1000.0):
    """How many settled non-test transactions exceed the threshold."""
    return sum(1 for amt in _settled_amounts(path) if amt > threshold_usd)


# --- The single-use gotcha, demonstrated -----------------------------------
# Plain words: a generator is a one-way stream. Two drinkers need two
# streams — re-create the generator (cheap) instead of reusing it.

def stream_demo():
    """Show that reusing one generator starves the second consumer."""
    gen = (x * x for x in range(5))
    first = list(gen)    # [0, 1, 4, 9, 16] — stream is now spent
    second = list(gen)   # [] — nothing left!
    return first, second


if __name__ == "__main__":
    import tempfile, os

    txns = [
        {"status": "settled", "is_test": False, "amount_usd": 25.50},
        {"status": "pending", "is_test": False, "amount_usd": 99.99},
        {"status": "settled", "is_test": True, "amount_usd": 10.00},
        {"status": "settled", "is_test": False, "amount_usd": 1500.00},
        {"status": "settled", "is_test": False},  # missing amount -> 0
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                     delete=False) as f:
        for t in txns:
            f.write(json.dumps(t) + "\n")
        path = f.name

    print(daily_settled_volume(path))          # 1525.5
    print(count_large_settled(path))           # 1
    assert daily_settled_volume(path) == \
        daily_settled_volume_eager(path)       # same answer, ~1 row in RAM
    print(stream_demo())  # ([0, 1, 4, 9, 16], []) — single-use!
    os.unlink(path)
