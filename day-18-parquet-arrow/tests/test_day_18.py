"""Day 18 tests — every solution must pass before the day is committed.

The suite practices what the day preaches: assertions about what
was READ, not just what was returned. Schemas, footers, and folder
layouts are checked directly — no timing bets, no wall-clock.
"""
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_column_select import (
    read_two_columns,
    write_same_as_csv,
    write_wide_table,
)
from problem_02_predicate_pushdown import (
    read_big_amounts,
    row_group_stats,
    write_sorted_events,
)
from problem_03_partition_pruning import (
    partition_dirs,
    read_october,
    write_partitioned,
)
from problem_04_schema_and_types import (
    SCHEMA,
    read_schema,
    write_strings_default_dict,
    write_strings_no_dict,
    write_typed_events,
)
from problem_05_arrow_zero_copy import (
    from_arrow,
    safe_cast_amounts,
    select_columns,
    shared_buffer_count,
    to_arrow,
)

NARROW = ["user_id", "amount"]


# --- Problem 1: column select ------------------------------------------------

def test_column_select_returns_only_requested(tmp_path):
    p = tmp_path / "wide.parquet"
    full = write_wide_table(str(p))
    narrow = read_two_columns(str(p))
    assert narrow.schema.names == NARROW
    assert narrow.num_rows == full.num_rows == 1_000
    assert narrow.column("user_id").to_pylist() == full.column("user_id").to_pylist()
    assert narrow.column("amount").to_pylist() == full.column("amount").to_pylist()


def test_columnar_beats_csv_on_size(tmp_path):
    p_parquet = tmp_path / "wide.parquet"
    p_csv = tmp_path / "wide.csv"
    full = write_wide_table(str(p_parquet), n_rows=2_000)
    write_same_as_csv(str(p_csv), full)
    assert p_parquet.stat().st_size < p_csv.stat().st_size


# --- Problem 2: predicate pushdown ------------------------------------------

def test_pushdown_returns_right_rows(tmp_path):
    p = tmp_path / "events.parquet"
    write_sorted_events(str(p))
    got = read_big_amounts(str(p), threshold=2_000)
    assert got.num_rows == 999  # amounts 2001..2999
    assert got.column("amount").to_pylist() == list(range(2_001, 3_000))


def test_footer_stats_describe_disjoint_ranges(tmp_path):
    p = tmp_path / "events.parquet"
    write_sorted_events(str(p))
    stats = row_group_stats(str(p))
    assert len(stats) == 3
    assert stats[0] == (0, 999, 1_000)
    assert stats[1] == (1_000, 1_999, 1_000)
    assert stats[2] == (2_000, 2_999, 1_000)
    # row group 1's max (1999) < threshold (2000): it can prove it never matches
    assert stats[1][1] <= 2_000


# --- Problem 3: partition pruning --------------------------------------------

def test_partition_layout_is_hive_style(tmp_path):
    root = tmp_path / "events"
    write_partitioned(str(root))
    dirs = partition_dirs(str(root))
    parents = sorted({str(Path(d).parent) for d in dirs})
    assert parents == [
        "year=2025/month=12",
        "year=2026/month=10",
        "year=2026/month=9",
    ]
    assert all(d.endswith(".parquet") for d in dirs)
    assert len(dirs) == 3  # one file per partition


def test_pruned_read_returns_only_october(tmp_path):
    root = tmp_path / "events"
    write_partitioned(str(root))
    got = read_october(str(root))
    assert got.num_rows == 10
    assert set(got.column("month").to_pylist()) == {10}
    assert set(got.column("year").to_pylist()) == {2026}
    assert got.column("event_id").to_pylist() == [f"e-{100 + i}" for i in range(10)]


# --- Problem 4: schema and types ----------------------------------------------

def test_schema_round_trips_exactly(tmp_path):
    p = tmp_path / "typed.parquet"
    write_typed_events(str(p))
    assert read_schema(str(p)).equals(SCHEMA)


def test_dictionary_encoding_is_the_default_win(tmp_path):
    p_dict = tmp_path / "dict.parquet"
    p_plain = tmp_path / "plain.parquet"
    write_strings_default_dict(str(p_dict))
    write_strings_no_dict(str(p_plain))
    # same 60,000 repeated strings: the default dictionary encoding
    # stores them ~150x smaller than raw strings
    assert p_dict.stat().st_size * 10 < p_plain.stat().st_size
    assert pq.read_schema(str(p_dict)).field("status").type == pa.string()
    assert pq.read_schema(str(p_plain)).field("status").type == pa.string()
    # values identical either way — encoding is storage, not semantics
    assert (pq.read_table(str(p_dict), columns=["status"]).to_pylist()
            == pq.read_table(str(p_plain), columns=["status"]).to_pylist())


def test_typed_values_survive(tmp_path):
    p = tmp_path / "typed.parquet"
    write_typed_events(str(p), n_rows=10)
    got = pq.read_table(str(p))
    assert got.column("amount").to_pylist() == [i * 7 for i in range(10)]
    assert got.column("status").to_pylist() == (
        ["ok", "retry", "failed", "ok", "retry"] * 2
    )


# --- Problem 5: arrow zero-copy -------------------------------------------------

def test_round_trip_keeps_values_and_types():
    import pandas as pd

    df = pd.DataFrame({"user_id": ["u-1", "u-2"], "amount": [10, 20]})
    table = to_arrow(df)
    assert isinstance(table, pa.Table)
    back = from_arrow(table)
    assert back["user_id"].tolist() == ["u-1", "u-2"]
    assert back["amount"].tolist() == [10, 20]


def test_select_shares_buffers_not_copies():
    import pandas as pd

    df = pd.DataFrame({
        "a": list(range(100)),
        "b": [f"s-{i}" for i in range(100)],
        "c": [float(i) for i in range(100)],
    })
    table = to_arrow(df)
    narrowed = select_columns(table, ["a"])
    assert narrowed.schema.names == ["a"]
    assert narrowed.num_rows == 100
    assert shared_buffer_count(table, narrowed) > 0  # same memory, new lens


def test_safe_cast_rejects_overflow():
    table = pa.table({"amount": pa.array([2**40], type=pa.int64())})
    with pytest.raises(pa.ArrowInvalid):
        safe_cast_amounts(table)
    ok = pa.table({"amount": pa.array([42], type=pa.int64())})
    assert safe_cast_amounts(ok).to_pylist() == [42]
