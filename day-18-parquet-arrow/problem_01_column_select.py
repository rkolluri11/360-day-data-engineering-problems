"""Problem 1 — column select: read 2 of 50 columns, skip the other 48
===============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A CSV stores ROWS: every line carries every column. To read
``user_id`` and ``amount`` out of a 50-column CSV, the parser
reads all 50 columns of every row, splits every comma, and then
you throw 96% of it away:

    # csv: reads 50 columns x N rows to give you 2
    df = pd.read_csv("events.csv", usecols=["user_id", "amount"])

Parquet stores COLUMNS: each column is its own contiguous run
of bytes. Ask for 2 of 50 and the reader seeks straight past
the other 48 — they are never read, never parsed:

    # parquet: the other 48 columns never leave the disk
    table = pq.read_table("events.parquet",
                          columns=["user_id", "amount"])

Plain words: a CSV is one long scroll with everything
interleaved. Parquet is a library where every subject has its
own shelf — you walk to the history shelf and ignore the rest.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Column select only helps if the file is COLUMNAR. Asking
    for ``usecols`` on a CSV still parses every byte; the
    format decides, not the argument.
  - Wide tables with hundreds of columns are where this wins
    biggest: telemetry, clickstreams, feature stores. A 2-of-200
    select is a 99% I/O cut, not 10%.
  - Small files (< a few MB) can read SLOWER as Parquet — the
    metadata seek costs more than just scanning. Columnar
    pays off at scale, not on toy files.
  - Selecting columns changes NOTHING about row count: you
    get every row, only fewer columns. Confusing "narrower"
    with "fewer rows" is the classic beginner bug.

Your solution: ``write_wide_table`` and ``read_two_columns``
are already written. The tests prove the read returns exactly
the two requested columns with identical values — and that the
Parquet file is dramatically smaller than the same data as CSV.

ANALOGY
-------
Column select is ordering two dishes from a 50-item menu. The
kitchen cooks those two. A row-format read is a buffet where
you must walk past all 50 trays to reach your table.
"""
import pyarrow as pa
import pyarrow.parquet as pq


def write_wide_table(path, n_rows=1_000, n_cols=50):
    """Write a wide table: id + amount + 48 filler columns."""
    columns = {
        "user_id": pa.array([f"u-{i}" for i in range(n_rows)]),
        "amount": pa.array([float(i) * 1.5 for i in range(n_rows)]),
    }
    for c in range(n_cols - 2):
        columns[f"filler_{c:02d}"] = pa.array([c * 1000 + i for i in range(n_rows)])
    table = pa.table(columns)
    pq.write_table(table, path)
    return table


def read_two_columns(path):
    """Read only user_id and amount — the other 48 columns stay on disk."""
    return pq.read_table(path, columns=["user_id", "amount"])


def write_same_as_csv(path, table):
    """Same data as CSV, for the size comparison nobody believes."""
    import pandas as pd

    table.to_pandas().to_csv(path, index=False)
