"""Problem 2 — predicate pushdown: whole row groups skip themselves
===============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Parquet splits a file into ROW GROUPS (chunks of rows, often
~1M each). Every row group stores MIN/MAX statistics per
column in the file footer. When you read with a filter, the
reader checks the footer FIRST:

    # amount > 1000? row groups whose max <= 1000 are skipped
    # WITHOUT reading a single row from them
    table = pq.read_table("events.parquet",
                          filters=[("amount", ">", 1000)])

If your data is sorted (or even roughly ordered) by the
filtered column, whole row groups prove they cannot match and
are never touched.

Plain words: each row group has a label on the box — "amounts
0 to 500". Your filter says "> 1000". The box never gets
opened.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Pushdown is only as good as your SORT ORDER. Randomly
    ordered data means every row group's min/max spans the
    whole range, and nothing gets skipped. Sort (or cluster)
    by your most-filtered columns at write time.
  - Statistics are per row group, so SMALL row groups give
    finer skipping at the cost of more footer metadata.
    Tune ``row_group_size`` to your filter patterns.
  - Only certain predicates push down: comparisons on the
    column itself. A filter on ``amount * 1.1 > 1000`` or a
    Python-side function runs AFTER the read — no skipping.
  - NULL-heavy columns weaken min/max stats. Know your
    null rate before betting the pipeline on pushdown.

Your solution: ``write_sorted_events`` and ``read_big_amounts``
are already written. The tests prove the filter returns the
right rows AND that the footer statistics genuinely describe
disjoint ranges — the thing that makes the skipping possible.

ANALOGY
-------
Predicate pushdown is a library catalog. You want books after
2010; the catalog tells you the history wing holds 1980–2005,
so you never walk there. Without the catalog you open every
book.
"""
import pyarrow as pa
import pyarrow.parquet as pq


def write_sorted_events(path, n_rows=3_000, row_group_size=1_000):
    """Write events sorted by amount, in 3 row groups of 1,000."""
    amounts = list(range(n_rows))  # 0..2999, sorted by construction
    table = pa.table({
        "event_id": pa.array([f"e-{i}" for i in range(n_rows)]),
        "amount": pa.array(amounts, type=pa.int64()),
    })
    pq.write_table(table, path, row_group_size=row_group_size)
    return table


def read_big_amounts(path, threshold=2_000):
    """Rows with amount > threshold — row groups 1 and 2 skip themselves."""
    return pq.read_table(path, filters=[("amount", ">", threshold)])


def row_group_stats(path):
    """Min/max per row group, straight from the footer. The skipping proof."""
    meta = pq.read_metadata(path)
    stats = []
    for rg in range(meta.num_row_groups):
        col = meta.row_group(rg).column(1)  # the amount column
        s = col.statistics
        stats.append((s.min, s.max, meta.row_group(rg).num_rows))
    return stats
