"""Problem 3 — partition pruning: folders are the index
========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A partitioned dataset stores data in folders named after
column values — Hive style:

    events/
      year=2026/month=09/part-0.parquet
      year=2026/month=10/part-0.parquet
      year=2025/month=12/part-0.parquet

Filter on a partition column and the reader skips entire
folders WITHOUT opening a single file inside them:

    table = pq.read_table("events/",
                          filters=[("year", "=", 2026),
                                   ("month", "=", 10)])

Two filters, one folder read, two folders never touched.

Plain words: partitions are labeled drawers. "October 2026"
is written on one drawer — you open that drawer. You do not
open every drawer and check each sock's date.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Partition on what you FILTER, not what is convenient.
    Partitioning by ``event_id`` creates millions of tiny
    files (the small-files problem); partitioning by a
    column you never filter on buys you nothing.
  - Too many partitions is its own outage: 100k folders
    means 100k file listings on every read. Keep partition
    counts in the low thousands; prefer year/month over
    year/month/day/hour unless you truly query by hour.
  - Partition columns come back as strings/dictionary by
    default — cast them in your schema or your "2026" is
    a string and your joins silently miss.
  - Writing one file per partition is slow; writing is the
    expensive side of partitioning. Batch small partitions
    or accept the write cost for the read win.

Your solution: ``write_partitioned`` and ``read_october``
are already written. The tests prove the layout has the
expected folders AND that the filtered read returns exactly
October's rows — pruning you can see in the directory tree.

ANALOGY
-------
Partition pruning is a filing cabinet. Ask for October and
you pull the October drawer. The unpartitioned alternative
is one giant box labeled "stuff" that you dump on the floor.
"""
import pyarrow as pa
import pyarrow.parquet as pq


def write_partitioned(root_path):
    """Three months of events, Hive-partitioned by year and month."""
    rows = []
    for year, month, start in [(2026, 9, 0), (2026, 10, 100), (2025, 12, 200)]:
        for i in range(10):
            rows.append((year, month, f"e-{start + i}", (start + i) * 10))
    table = pa.table({
        "year": pa.array([r[0] for r in rows], type=pa.int32()),
        "month": pa.array([r[1] for r in rows], type=pa.int32()),
        "event_id": pa.array([r[2] for r in rows]),
        "amount": pa.array([r[3] for r in rows], type=pa.int64()),
    })
    pq.write_to_dataset(table, root_path=root_path,
                        partition_cols=["year", "month"])
    return table


def read_october(root_path):
    """Only year=2026/month=10 — the other two folders are never opened."""
    return pq.read_table(root_path,
                         filters=[("year", "=", 2026), ("month", "=", 10)])


def partition_dirs(root_path):
    """The folder layout, relative to root — pruning made visible."""
    from pathlib import Path

    return sorted(
        str(p.relative_to(root_path))
        for p in Path(root_path).rglob("*.parquet")
    )
