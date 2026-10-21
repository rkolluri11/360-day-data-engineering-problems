"""Problem 5 — Arrow in memory: one layout, zero copies
==========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Moving data between tools usually means SERIALIZING: pandas
turns a frame into bytes, the next tool parses the bytes
back. Every handoff copies the data and burns CPU on
formatting it twice.

Apache Arrow defines ONE in-memory columnar layout. pandas,
DuckDB, Polars, and Spark can all read the same bytes IN
PLACE — no serialize, no parse, no copy:

    table = pa.Table.from_pandas(df)   # Arrow takes the layout
    df2 = table.to_pandas()            # back, without a round trip

A slice is a VIEW over the same buffers, not a copy:

    just_amounts = table.select(["amount"])  # same memory, new lens

Plain words: Arrow is the shared whiteboard. Every tool
reads the same board instead of each one photocopying it,
marking up its copy, and photocopying it back.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - "Zero-copy" has limits: ``to_pandas()`` copies when
    pandas needs something Arrow doesn't have (e.g. its
    own nullable dtypes in older versions). Design the
    handoff around what both sides natively support.
  - Arrow tables are IMMUTABLE. Every "modification" makes
    a new table sharing buffers with the old one — great
    for safety, surprising if you expected in-place edits.
    Chunked arrays grow by appending chunks, not resizing.
  - IPC (the Arrow wire format) is the fast path between
    processes: ``pa.ipc`` streams beat Parquet files for
    ephemeral handoffs, Parquet wins for anything stored.
  - Type mismatches at the boundary are silent-ish:
    ``pa.Table.from_pandas`` with a pandas ``object``
    column gives you whatever it infers. Cast explicitly
    with ``pa.compute.cast`` (``safe=True``) at the edge.

Your solution: the handoff helpers are already written. The
tests prove the pandas -> Arrow -> pandas round trip keeps
values and types, that ``select`` narrows without copying
buffers, and that an explicit safe cast rejects bad data
instead of guessing.

ANALOGY
-------
Arrow is a shared Google Doc. Everyone edits the same
document. The old way is emailing Word files back and
forth — "final_v2_REALLY_FINAL.docx" — and merging by hand.
"""
import pyarrow as pa
import pyarrow.compute as pc


def to_arrow(df):
    """pandas -> Arrow: one layout from here on."""
    return pa.Table.from_pandas(df, preserve_index=False)


def from_arrow(table):
    """Arrow -> pandas: back without a serialize round trip."""
    return table.to_pandas()


def select_columns(table, names):
    """Narrow to `names` — a view over the same buffers, not a copy."""
    return table.select(names)


def shared_buffer_count(table, narrowed):
    """How many data buffers the narrowed table shares with the parent."""
    parent_ids = {id(b) for col in table.columns for chunk in col.chunks
                  for b in chunk.buffers() if b is not None}
    child_ids = {id(b) for col in narrowed.columns for chunk in col.chunks
                 for b in chunk.buffers() if b is not None}
    return len(parent_ids & child_ids)


def safe_cast_amounts(table):
    """Cast amount to int32, SAFE: overflow raises instead of wrapping."""
    return pc.cast(table.column("amount"), pa.int32(), safe=True)
