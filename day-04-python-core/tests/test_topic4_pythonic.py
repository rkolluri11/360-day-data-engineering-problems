"""Tests for Day 4 Topic 4 — Pythonic Programming (problems 16-20)."""

import json
import os
import sys
import tempfile
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from problem_16_pythonic_transform_filter import parse_orders, parse_orders_loop
from problem_17_pythonic_index_build import (
    build_latest_index,
    enrich_orders,
    latest_address_scan,
)
from problem_18_pythonic_merge_aligned import merge_feeds, merge_feeds_loose
from problem_19_pythonic_quality_gates import (
    gate_eager,
    has_pii_leak,
    partition_ready,
)
from problem_20_pythonic_genexpr_pipeline import (
    _settled_amounts,
    count_large_settled,
    daily_settled_volume,
    daily_settled_volume_eager,
    stream_demo,
)


# --- Problem 16: transform + filter in one pass ----------------------------

def _raw_events():
    return [
        {"order_id": "o1", "customer_id": "c9", "amount_cents": 2599,
         "event_time": "2026-10-06T20:00:00Z"},
        {"order_id": "o2", "customer_id": "c9"},                    # no amount
        {"order_id": "o3", "customer_id": "c4", "amount_cents": -500,
         "event_time": "2026-10-06T20:01:00Z"},                     # refund
        {"customer_id": "c1", "amount_cents": 100},                 # no order_id
        {"order_id": "o4", "amount_cents": 0},                      # zero is valid
    ]


def test_p16_filters_and_converts():
    out = parse_orders(_raw_events())
    assert [r["order_id"] for r in out] == ["o1", "o4"]
    assert out[0]["amount_usd"] == 25.99
    assert out[0]["event_time"] == "2026-10-06T20:00:00Z"
    assert out[1]["customer_id"] is None  # missing key -> None, no crash


def test_p16_matches_loop_version():
    assert parse_orders(_raw_events()) == parse_orders_loop(_raw_events())


def test_p16_empty_input():
    assert parse_orders([]) == []


# --- Problem 17: dict-comprehension index -----------------------------------

_ADDRESSES = [
    {"customer_id": "c1", "city": "Austin", "updated_at": "2026-09-01"},
    {"customer_id": "c2", "city": "Denver", "updated_at": "2026-09-05"},
    {"customer_id": "c1", "city": "Dallas", "updated_at": "2026-10-02"},
]


def test_p17_newest_wins():
    index = build_latest_index(_ADDRESSES)
    assert index["c1"]["city"] == "Dallas"
    assert index["c2"]["city"] == "Denver"


def test_p17_matches_scan_version():
    index = build_latest_index(_ADDRESSES)
    assert index["c1"] == latest_address_scan("c1", _ADDRESSES)


def test_p17_enrich_unknown_customer_gets_none():
    index = build_latest_index(_ADDRESSES)
    out = enrich_orders([{"order_id": "o1", "customer_id": "c9"}], index)
    assert out[0]["ship_to"] is None


# --- Problem 18: strict zip + enumerate --------------------------------------

def test_p18_aligned_merge():
    rows = merge_feeds(["10:00", "10:01"], [21.5, 21.7], ["C", "C"])
    assert rows == [
        {"row": 0, "ts": "10:00", "reading": 21.5, "unit": "C"},
        {"row": 1, "ts": "10:01", "reading": 21.7, "unit": "C"},
    ]


def test_p18_mismatch_raises_not_truncates():
    with pytest.raises(ValueError, match="mismatch"):
        merge_feeds(["10:00", "10:01", "10:02"], [21.5, 21.7], ["C", "C", "C"])


def test_p18_matches_loose_on_clean_input():
    ts = ["10:00", "10:01"]
    assert merge_feeds(ts, [1.0, 2.0], ["C", "C"]) == \
        merge_feeds_loose(ts, [1.0, 2.0], ["C", "C"])


# --- Problem 19: any/all quality gates ---------------------------------------

_GOOD_MANIFEST = [{"name": "orders.csv", "landed": True},
                  {"name": "customers.csv", "landed": True}]


def test_p19_certifies_clean_partition():
    rows = ({"order_id": f"o{i}", "amount_cents": 100} for i in range(100))
    ready, reason = partition_ready(_GOOD_MANIFEST, rows)
    assert ready is True
    assert reason == "partition certified"


def test_p19_reports_first_violation():
    rows = [{"order_id": "o1", "amount_cents": 100},
            {"order_id": None, "amount_cents": 50}]
    ready, reason = partition_ready(_GOOD_MANIFEST, rows)
    assert ready is False
    assert "row 1" in reason and "null order_id" in reason


def test_p19_short_circuits_on_first_bad_row():
    consumed = []

    def gen():
        for i in range(1_000_000):
            consumed.append(i)
            yield {"order_id": None if i == 3 else f"o{i}", "amount_cents": 1}

    ready, _ = partition_ready(_GOOD_MANIFEST, gen())
    assert ready is False
    assert len(consumed) < 10  # stopped at row 3, not row 1,000,000


def test_p19_missing_file_fails_fast():
    manifest = [{"name": "orders.csv", "landed": False}]
    ready, reason = partition_ready(manifest, [])
    assert ready is False
    assert "orders.csv" in reason


def test_p19_pii_leak_detection():
    assert has_pii_leak([{"email": "a@x.com", "email_masked": False}]) is True
    assert has_pii_leak([{"email": "a@x.com", "email_masked": True}]) is False
    assert has_pii_leak([{"email_masked": False}]) is False  # no email at all


def test_p19_matches_eager_gate():
    rows = [{"order_id": "o1", "amount_cents": 100}]
    assert partition_ready(_GOOD_MANIFEST, rows)[0] == \
        gate_eager(_GOOD_MANIFEST, rows)[0]


# --- Problem 20: generator-expression pipelines ------------------------------

@pytest.fixture()
def jsonl_path():
    txns = [
        {"status": "settled", "is_test": False, "amount_usd": 25.50},
        {"status": "pending", "is_test": False, "amount_usd": 99.99},
        {"status": "settled", "is_test": True, "amount_usd": 10.00},
        {"status": "settled", "is_test": False, "amount_usd": 1500.00},
        {"status": "settled", "is_test": False},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                     delete=False) as f:
        for t in txns:
            f.write(json.dumps(t) + "\n")
        path = f.name
    yield path
    os.unlink(path)


def test_p20_streaming_total(jsonl_path):
    assert daily_settled_volume(jsonl_path) == 1525.50


def test_p20_matches_eager_total(jsonl_path):
    assert daily_settled_volume(jsonl_path) == \
        daily_settled_volume_eager(jsonl_path)


def test_p20_pipeline_is_lazy(jsonl_path):
    gen = _settled_amounts(jsonl_path)
    assert isinstance(gen, types.GeneratorType)  # a pipe, not a bucket
    assert next(gen) == 25.50  # pulls one item on demand


def test_p20_count_large(jsonl_path):
    assert count_large_settled(jsonl_path) == 1
    assert count_large_settled(jsonl_path, threshold_usd=10.0) == 2


def test_p20_generator_single_use():
    first, second = stream_demo()
    assert first == [0, 1, 4, 9, 16]
    assert second == []  # spent stream yields nothing
