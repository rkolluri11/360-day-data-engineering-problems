"""Problem 4 — schema and types: CSV guesses, Parquet knows
===========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A CSV has no types. ``"10,"``, ``"N/A"``, ``""`` all look like
text, and pandas guesses per chunk — so row 9,000,001 can
crash a pipeline that read 9,000,000 rows fine. Parquet stores
a SCHEMA with the data: this column IS int64, that one IS a
timestamp, no guessing, no per-chunk surprises.

Dictionary encoding goes further: a string column with few
distinct values (status codes, regions) is stored once as a
dictionary plus tiny integer keys — often 100x smaller than
the raw strings. Parquet does this BY DEFAULT; turning it
off on repetitive strings is the fastest way to watch a
file explode.

    schema = pa.schema([
        ("user_id", pa.string()),
        ("status", pa.dictionary(pa.int32(), pa.string())),
        ("amount", pa.int64()),
        ("ts", pa.timestamp("us")),
    ])
    pq.write_table(table, "events.parquet", schema=schema)

Plain words: CSV is a handshake deal — "trust me, that's a
number." Parquet is a signed contract with the types written
into the file itself.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Schema EVOLUTION is the real skill: adding a nullable
    column is safe; renaming one silently breaks downstream
    selects; changing int32 to int64 is fine, int64 to
    int32 is data loss. Version your schemas like APIs.
  - Dictionary encoding backfires on HIGH-cardinality
    columns (uuids, free text): the dictionary itself gets
    huge and lookups slow down. Encode low-cardinality
    strings, leave the snowflakes alone.
  - Timestamps need a UNIT (s/ms/us/ns) and a TIMEZONE
    decision. Mixed units across files is the classic
    "why is everything off by 1000x" incident.
  - Compression is a knob, not a default: snappy for speed
    (hot data), zstd for size (cold data). Gzip sits in the
    middle and pleases nobody.

Your solution: ``write_typed_events`` and friends are already
written. The tests prove the schema round-trips exactly,
dictionary encoding shrinks repeated strings, and the Parquet
file beats the CSV on size — the contract, in bytes.

ANALOGY
-------
A schema is the ingredient list on a food label. CSV is a
mystery stew — you find out what's in it by tasting. Parquet
tells you up front, and the label is legally binding.
"""
import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA = pa.schema([
    ("user_id", pa.string()),
    ("status", pa.dictionary(pa.int32(), pa.string())),
    ("amount", pa.int64()),
    ("ts", pa.timestamp("us")),
])


def write_typed_events(path, n_rows=2_000):
    """Statuses repeat (dictionary-friendly); amounts and timestamps are typed."""
    statuses = ["ok", "retry", "failed", "ok", "retry"] * (n_rows // 5)
    table = pa.table({
        "user_id": pa.array([f"u-{i}" for i in range(n_rows)]),
        "status": pa.array(statuses,
                           type=pa.dictionary(pa.int32(), pa.string())),
        "amount": pa.array([i * 7 for i in range(n_rows)], type=pa.int64()),
        "ts": pa.array([1_700_000_000_000_000 + i for i in range(n_rows)],
                       type=pa.timestamp("us")),
    }, schema=SCHEMA)
    pq.write_table(table, path, compression="snappy")
    return table


def read_schema(path):
    """The contract, straight from the file footer."""
    return pq.read_schema(path)


def write_strings_no_dict(path, n_rows=60_000):
    """Same repeated statuses with dictionary encoding DISABLED.

    Parquet dictionary-encodes strings BY DEFAULT. This helper
    turns it off so you can see what the default was saving you.
    """
    statuses = (["payment_status_completed_ok"] * (n_rows // 3)
                + ["payment_status_retry_pending"] * (n_rows // 3)
                + ["payment_status_failed_final"] * (n_rows // 3))
    table = pa.table({"status": pa.array(statuses)})
    pq.write_table(table, path, use_dictionary=False)
    return table


def write_strings_default_dict(path, n_rows=60_000):
    """Same data, dictionary encoding ON (the Parquet default)."""
    statuses = (["payment_status_completed_ok"] * (n_rows // 3)
                + ["payment_status_retry_pending"] * (n_rows // 3)
                + ["payment_status_failed_final"] * (n_rows // 3))
    table = pa.table({"status": pa.array(statuses)})
    pq.write_table(table, path)  # use_dictionary=True is the default
    return table
