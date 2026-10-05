"""Problem 1 — The 2 GB CSV sum
==============================

THE PROBLEM (beginner foothold first)
------------------------------------
You have a CSV file with one column of numbers:

    amount
    12.50
    7.25
    ...

It is 2 GB on disk — far bigger than the RAM you want to spend on it.
Write ``total_amount(path)`` that returns the sum of the ``amount``
column, using roughly the same memory whether the file is 2 MB or 2 GB.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The naive version — ``sum(float(r["amount"]) for r in list(reader))`` or
loading everything into a list first — turns 2 GB of CSV text into
4–10 GB of Python objects and gets the container OOMKilled. Your
solution must stream: it may only ever hold one row in memory at a time.

Plain words: this solution reads the file one line at a time, adds each
number to a running total, and forgets the line immediately. Like
counting money by adding each bill to a tally instead of piling every
bill on the table first.

ANALOGY
-------
A page-at-a-time reader finishes any book. A memorize-the-whole-book
reader finishes only short books.
"""

from __future__ import annotations

import csv


def total_amount(path: str) -> float:
    """Return the sum of the ``amount`` column of a CSV file, streaming.

    Uses O(1) memory regardless of file size.
    """
    total = 0.0
    with open(path, "r", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            total += float(row["amount"])
    return total


if __name__ == "__main__":
    import sys

    print(total_amount(sys.argv[1]))
