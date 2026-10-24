"""Day 20 - Problem 4: Parquet vs JSON — the size nobody believes.

THE PROBLEM (beginner foothold first)
------------------------------------
JSON stores every value as text, with every key repeated on
every row. Parquet stores each COLUMN as a tight run of typed
bytes — dictionary-encoded strings, packed numbers. For a wide
table the difference is not 10%: it is an order of magnitude:

    # same 1,000 x 20 table
    events.json    -> every key, every row, as text
    events.parquet -> each column once, typed and compressed

And because Parquet is columnar, reading 2 of 20 columns never
touches the other 18 on disk (see Day 18).

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - JSON is row-oriented: even ``usecols`` on a CSV/JSON read
    still parses every byte. Columnar is a property of the
    FORMAT, not the reader argument.
  - Small files can read SLOWER as Parquet — the footer seek
    costs more than scanning a few KB. Columnar pays off at
    scale, not on toy files.
  - Parquet carries a real schema: types are known per file,
    not guessed per chunk. The ``"19.99"``-vs-``19.99`` drift
    from Problem 1 cannot happen.
  - JSON wins where humans read: logs, API payloads, configs.
    Parquet wins where machines scan: lakes, features, exports.

Your solution: ``write_json_lines``, ``write_parquet_table``,
``read_columns``, and ``compare_sizes`` are already written.
The tests prove Parquet is dramatically smaller for wide
numeric data — and that a column select returns exactly the
requested columns with identical values.

ANALOGY
-------
JSON is the labeled cardboard box: openable by anyone, bulky.
Parquet is the warehouse pallet: useless for moving one mug,
perfect for moving ten thousand.
"""
import json
import os

import pyarrow as pa
import pyarrow.parquet as pq


def make_table(n_rows=1_000, n_cols=20):
    """A wide table: user_id + amount + filler columns."""
    columns = {
        "user_id": pa.array([f"u-{i}" for i in range(n_rows)]),
        "amount": pa.array([float(i) * 1.5 for i in range(n_rows)]),
    }
    for c in range(n_cols - 2):
        columns[f"filler_{c:02d}"] = pa.array([c * 1000 + i for i in range(n_rows)])
    return pa.table(columns)


def write_json_lines(table, path):
    """Write ``table`` as JSON lines (one object per row)."""
    rows = table.to_pylist()
    with open(path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def write_parquet_table(table, path):
    """Write ``table`` as Parquet."""
    pq.write_table(table, path)


def read_columns(path, columns):
    """Read only ``columns`` from the Parquet file — the rest stays on disk."""
    return pq.read_table(path, columns=columns)


def compare_sizes(json_path, parquet_path):
    """Return {format: bytes} for the two files on disk."""
    return {
        "json": os.path.getsize(json_path),
        "parquet": os.path.getsize(parquet_path),
    }


if __name__ == "__main__":
    import tempfile

    table = make_table()
    with tempfile.TemporaryDirectory() as tmp:
        jp, pp = f"{tmp}/events.json", f"{tmp}/events.parquet"
        write_json_lines(table, jp)
        write_parquet_table(table, pp)
        sizes = compare_sizes(jp, pp)
        print(f"json: {sizes['json']:,} bytes")
        print(f"parquet: {sizes['parquet']:,} bytes")
        print(f"ratio: {sizes['json'] / sizes['parquet']:.1f}x")
        sub = read_columns(pp, ["user_id", "amount"])
        print("selected columns:", sub.column_names, "| rows:", sub.num_rows)
