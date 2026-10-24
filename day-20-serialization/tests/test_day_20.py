"""Day 20 tests: serialization tradeoffs - JSON vs Avro vs Parquet vs Pickle."""
import json
import pickle
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_json_roundtrip import json_roundtrip, json_type_report
from problem_02_pickle_boundary import (
    trusted_roundtrip,
    scan_pickle_ops,
    craft_malicious_pickle,
)
from problem_03_avro_schema import (
    SCHEMA_V1,
    SCHEMA_V2,
    write_records,
    read_records,
    evolve,
)
from problem_04_parquet_vs_json import (
    make_table,
    write_json_lines,
    write_parquet_table,
    read_columns,
    compare_sizes,
)
from problem_05_choose_format import choose_format


# --- Problem 1: JSON roundtrip ---
def test_json_roundtrip_values_survive():
    record = {"user_id": "u-7", "amount": 19.99, "n": 3, "ok": True}
    assert json_roundtrip(record) == record


def test_json_type_report_flags_tuple_shift():
    report = json_type_report({"tags": ("a", "b"), "n": 3})
    assert report["tags"] == ("tuple", "list")  # tuples come back as lists
    assert report["n"] == ("int", "int")


def test_json_type_report_stable_types():
    report = json_type_report({"user_id": "u-7", "amount": 19.99})
    assert all(before == after for before, after in report.values())


# --- Problem 2: pickle boundary ---
def test_trusted_roundtrip():
    obj = {"a": [1, 2, 3], "b": (4, 5)}
    assert trusted_roundtrip(obj) == obj


def test_benign_pickle_has_no_dangerous_ops():
    data = pickle.dumps({"user_id": "u-7", "amount": 19.99})
    assert scan_pickle_ops(data) == []


def test_malicious_pickle_lights_up_scan():
    data = craft_malicious_pickle()
    ops = scan_pickle_ops(data)
    names = [name for name, _arg in ops]
    # The payload references os.system (STACK_GLOBAL) and calls it (REDUCE).
    # The payload is only ever SCANNED, never loaded.
    assert "STACK_GLOBAL" in names
    assert "REDUCE" in names
    assert b"os" in data and b"system" in data


# --- Problem 3: Avro schema ---
def test_avro_exact_roundtrip():
    records = [
        {"user_id": "u-7", "amount": 19.99},
        {"user_id": "u-8", "amount": 4.50},
    ]
    assert read_records(write_records(records, SCHEMA_V1)) == records


def test_avro_evolution_fills_new_field_default():
    records = [{"user_id": "u-7", "amount": 19.99}]
    blob = write_records(records, SCHEMA_V1)
    evolved = evolve(blob)
    assert evolved[0]["user_id"] == "u-7"
    assert evolved[0]["nickname"] is None  # v2 default applied to v1 bytes


def test_avro_new_writer_old_data_readable():
    records = [{"user_id": "u-9", "amount": 1.25, "nickname": "nine"}]
    blob = write_records(records, SCHEMA_V2)
    back = read_records(blob)
    assert back[0]["nickname"] == "nine"


# --- Problem 4: parquet vs json ---
def test_parquet_dramatically_smaller_than_json(tmp_path):
    table = make_table(n_rows=1_000, n_cols=20)
    jp, pp = str(tmp_path / "e.json"), str(tmp_path / "e.parquet")
    write_json_lines(table, jp)
    write_parquet_table(table, pp)
    sizes = compare_sizes(jp, pp)
    assert sizes["parquet"] < sizes["json"] / 3  # not 10% - multiples


def test_column_select_returns_only_requested(tmp_path):
    table = make_table(n_rows=100, n_cols=20)
    pp = str(tmp_path / "e.parquet")
    write_parquet_table(table, pp)
    sub = read_columns(pp, ["user_id", "amount"])
    assert sub.column_names == ["user_id", "amount"]
    assert sub.num_rows == 100
    assert sub.column("user_id")[0].as_py() == "u-0"


# --- Problem 5: choose_format ---
def test_choose_format_happy_paths():
    assert choose_format(human_readable=True) == "json"
    assert choose_format(schema_evolution=True) == "avro"
    assert choose_format(columnar_scan=True) == "parquet"
    assert choose_format(python_only=True) == "pickle"


def test_choose_format_untrusted_never_pickle():
    # Even when pickle looks convenient, the trust boundary wins.
    assert choose_format(trusted=False, python_only=True) == "json"
    assert choose_format(trusted=False, human_readable=True) == "json"
    assert choose_format(trusted=False, schema_evolution=True) == "avro"


def test_choose_format_priority_order():
    # Human debugging outranks everything except trust.
    assert choose_format(human_readable=True, columnar_scan=True) == "json"
    # Schema evolution outranks columnar when both asked.
    assert choose_format(schema_evolution=True, columnar_scan=True) == "avro"
    # Safe default when nothing specified.
    assert choose_format() == "json"
