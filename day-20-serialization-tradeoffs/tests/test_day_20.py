"""Day 20 tests: serialization tradeoffs — JSON vs Avro vs Parquet vs Pickle (never Pickle)."""
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

try:  # fastavro >= 1.10 exposes it here...
    from fastavro.schema import SchemaResolutionError
except ImportError:  # ...older/newer builds keep it in _read_common
    from fastavro._read_common import SchemaResolutionError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_format_picker import DECISIONS, choose_format
from problem_02_schema_evolution import (
    SAMPLE,
    SCHEMA_V1,
    SCHEMA_V2_ADD_NO_DEFAULT,
    SCHEMA_V2_ADD_WITH_DEFAULT,
    is_safe_evolution,
    read_avro,
    write_avro,
)
from problem_03_pickle_landmine import (
    EXECUTED,
    PickleRefusedError,
    make_malicious_pickle,
    safe_deserialize,
    sniff_format,
)
from problem_04_size_speed_shootout import make_orders, shootout, to_avro, to_json, to_parquet
from problem_05_typed_envelope import (
    ENVELOPE_VERSION,
    SCHEMA,
    decode_typed,
    encode_typed,
    naive_dumps,
)


# --- Problem 1: the boundary decision ---
def test_choose_format_boundaries():
    assert choose_format("api")[0] == "json"
    assert choose_format("event-stream")[0] == "avro"
    assert choose_format("lake")[0] == "parquet"
    assert choose_format("debug")[0] == "json"
    assert choose_format("cache")[0] == "json"


def test_choose_format_never_pickle():
    assert all(fmt != "pickle" for fmt, _ in DECISIONS.values())


def test_choose_format_unknown_boundary_raises():
    with pytest.raises(ValueError):
        choose_format("carrier-pigeon")


# --- Problem 2: the contract that survives deploys ---
def test_avro_roundtrip_identity():
    assert read_avro(write_avro(SAMPLE, SCHEMA_V1)) == SAMPLE


def test_added_field_with_default_fills_old_records():
    rows = read_avro(write_avro(SAMPLE, SCHEMA_V1), SCHEMA_V2_ADD_WITH_DEFAULT)
    assert all(row["currency"] == "USD" for row in rows)
    assert [row["order_id"] for row in rows] == ["o-1", "o-2"]


def test_added_field_without_default_breaks_old_records():
    with pytest.raises(SchemaResolutionError):
        read_avro(write_avro(SAMPLE, SCHEMA_V1), SCHEMA_V2_ADD_NO_DEFAULT)


def test_is_safe_evolution_flags_the_breaking_change():
    assert is_safe_evolution(SCHEMA_V1, SCHEMA_V2_ADD_WITH_DEFAULT, SAMPLE) is True
    assert is_safe_evolution(SCHEMA_V1, SCHEMA_V2_ADD_NO_DEFAULT, SAMPLE) is False


# --- Problem 3: never unpickle a stranger's bytes ---
def test_unpickling_executes_code():
    EXECUTED.clear()
    import pickle

    pickle.loads(make_malicious_pickle())
    assert EXECUTED == ["pwned-by-pickle"]  # code ran at loads() time


def test_gate_refuses_pickle_by_default():
    with pytest.raises(PickleRefusedError):
        safe_deserialize(make_malicious_pickle())


def test_gate_allows_pickle_only_when_explicit():
    EXECUTED.clear()
    safe_deserialize(make_malicious_pickle(), allow_pickle=True)
    assert EXECUTED == ["pwned-by-pickle"]


def test_gate_decodes_json():
    assert safe_deserialize(b'{"order_id": "o-1"}') == {"order_id": "o-1"}


def test_sniff_magic_bytes():
    assert sniff_format(make_malicious_pickle()) == "pickle"
    assert sniff_format(b'  {"a": 1}') == "json"
    assert sniff_format(b"Obj\x01" + b"\x00" * 10) == "avro"
    assert sniff_format(b"PAR1" + b"\x00" * 10) == "parquet"


# --- Problem 4: the tradeoff table, executable ---
def test_shootout_size_ordering():
    records = make_orders(2000)
    sizes = {
        "json": len(to_json(records)),
        "avro": len(to_avro(records)),
        "parquet": len(to_parquet(records)),
    }
    assert sizes["avro"] < sizes["json"]  # binary rows beat text
    assert sizes["parquet"] < sizes["json"]  # columnar + compression beats text


def test_shootout_fidelity():
    table = shootout(n=500)
    assert all(row["faithful"] for row in table.values())
    assert set(table) == {"json", "avro", "parquet"}


def test_json_is_human_readable():
    payload = to_json(make_orders(3))
    assert b'"order_id"' in payload  # field names ride along, in the clear


# --- Problem 5: your types must survive the trip ---
def make_order():
    return {
        "order_id": "o-42",
        "amount": Decimal("19.99"),
        "qty": 3,
        "placed_at": datetime(2026, 10, 23, 19, 30, tzinfo=timezone.utc),
    }


def test_naive_json_rejects_decimal():
    with pytest.raises(TypeError):
        naive_dumps(make_order())


def test_naive_json_mangles_datetime():
    import json

    back = json.loads(json.dumps({"placed_at": make_order()["placed_at"]}, default=str))
    assert isinstance(back["placed_at"], str)  # the type died silently


def test_typed_envelope_restores_exact_types():
    order = make_order()
    back = decode_typed(encode_typed(order))
    assert back == order
    assert isinstance(back["amount"], Decimal)
    assert isinstance(back["placed_at"], datetime)
    assert back["placed_at"].tzinfo is not None


def test_typed_envelope_rejects_drift():
    payload = encode_typed(make_order())
    drifted = dict(SCHEMA)
    drifted["region"] = "string"
    with pytest.raises(ValueError):
        decode_typed(payload, drifted)
    import json

    tampered = json.loads(payload)
    tampered["v"] = "typed-json/99"
    with pytest.raises(ValueError):
        decode_typed(json.dumps(tampered).encode())
