"""Day 4 / Topic 1 tests — Python Foundations. Every solution must pass."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_foundations_type_coercion import coerce_batch, coerce_row
from problem_02_foundations_short_circuit import (
    all_of,
    any_of,
    is_valid_amount,
    make_settlement_filter,
    safe_float,
    with_default,
)
from problem_03_foundations_validation_branching import classify_batch, classify_row
from problem_04_foundations_chunked_loops import stream_totals, top_currency
from problem_05_foundations_identity_mutability import (
    dedupe_rows,
    get_batch_size,
    make_default_config,
    register_tenant,
    resolve_option,
    same_object,
)


# --- Problem 1: coerce_row / coerce_batch ---------------------------------

def test_01_currency_and_bool_words_coerce_cleanly():
    row = {"txn_id": "  A-1 ", "amount": "$1,234.56", "is_refund": "False",
           "quantity": "2"}
    schema = {"txn_id": "str", "amount": "float", "is_refund": "bool",
              "quantity": "int"}
    coerced, errors = coerce_row(row, schema)
    assert errors == []
    assert coerced == {"txn_id": "A-1", "amount": 1234.56,
                      "is_refund": False, "quantity": 2}


def test_01_bool_string_false_is_not_truthy():
    # The core trap: bool("False") is True. Our converter must say False.
    coerced, errors = coerce_row({"flag": "False"}, {"flag": "bool"})
    assert errors == []
    assert coerced["flag"] is False
    coerced, errors = coerce_row({"flag": "no"}, {"flag": "bool"})
    assert coerced["flag"] is False


def test_01_bad_cells_become_errors_not_exceptions():
    row = {"amount": "N/A", "is_refund": "maybe", "quantity": "12.5"}
    schema = {"amount": "float", "is_refund": "bool", "quantity": "int"}
    coerced, errors = coerce_row(row, schema)
    assert coerced["amount"] is None
    assert coerced["is_refund"] is None
    assert coerced["quantity"] is None  # int("12.5") must not truncate
    assert len(errors) == 3
    assert any("amount" in e and "float" in e for e in errors)


def test_01_batch_splits_good_and_bad_rows():
    schema = {"amount": "float"}
    good, bad = coerce_batch([{"amount": "10.0"}, {"amount": "N/A"},
                              {"amount": "1.2e3"}], schema)
    assert [r["amount"] for r in good] == [10.0, 1200.0]
    assert len(bad) == 1
    assert bad[0][0]["amount"] == "N/A"


# --- Problem 2: short-circuit filters ---------------------------------------

def test_02_is_valid_amount_guards_before_parsing():
    assert is_valid_amount("12.50") is True
    assert is_valid_amount("$1,234.56") is True
    assert is_valid_amount("") is False
    assert is_valid_amount(None) is False
    assert is_valid_amount("N/A") is False
    assert is_valid_amount("-4.00") is False   # negative is not a sale
    assert is_valid_amount("0") is False      # zero is not positive


def test_02_with_default_keeps_real_falsy_values():
    assert with_default(0, 10) == 0
    assert with_default("", "x") == ""
    assert with_default(False, True) is False
    assert with_default(None, 10) == 10


def test_02_settlement_filter_keeps_only_valid_usd_eur():
    keep = make_settlement_filter()
    assert keep({"amount": "12.50", "currency": "USD"}) is True
    assert keep({"amount": "20", "currency": "eur"}) is True   # case-insensitive
    assert keep({"amount": "", "currency": "USD"}) is False    # no crash
    assert keep({"amount": None, "currency": "EUR"}) is False  # no crash
    assert keep({"amount": "-5", "currency": "USD"}) is False
    assert keep({"amount": "9.99", "currency": "JPY"}) is False


def test_02_combinators_short_circuit():
    calls = []

    def expensive(row):
        calls.append("expensive")
        return True

    pred = all_of(lambda r: False, expensive)
    assert pred({}) is False
    assert calls == []  # expensive never ran

    pred = any_of(lambda r: True, expensive)
    assert pred({}) is True
    assert calls == []  # expensive never ran


def test_02_safe_float_never_raises():
    assert safe_float("$1,234.56") == 1234.56
    assert safe_float("1.2e3") == 1200.0
    assert safe_float("") is None
    assert safe_float(None) is None
    assert safe_float("N/A") is None
    assert safe_float("abc") is None


# --- Problem 3: classify_row -------------------------------------------------

def test_03_accepts_clean_row():
    row = {"transaction_id": "T-1", "amount": "42.50", "currency": "USD",
           "event_ts": "2026-10-06T10:00:00Z"}
    verdict, reasons = classify_row(row)
    assert verdict == "ACCEPT"
    assert reasons == []


def test_03_missing_fields_reject_and_zero_is_not_missing():
    verdict, reasons = classify_row({"transaction_id": "T-2", "amount": "",
                                     "currency": "USD"})
    assert verdict == "REJECT"
    assert any("amount" in r for r in reasons)
    # amount "0" is present-but-zero -> QUARANTINE, never REJECT-as-missing
    verdict, _ = classify_row({"transaction_id": "T-7", "amount": "0",
                               "currency": "USD"})
    assert verdict == "QUARANTINE"


def test_03_branch_order_and_exhaustiveness():
    assert classify_row({"transaction_id": "T", "amount": "5",
                         "currency": "XYZ"})[0] == "REJECT"
    assert classify_row({"transaction_id": "T", "amount": "-999.99",
                         "currency": "EUR"})[0] == "QUARANTINE"
    assert classify_row({"transaction_id": "T", "amount": "5",
                         "currency": "USD",
                         "event_ts": "2099-01-01T00:00:00Z"})[0] == "QUARANTINE"
    assert classify_row({"transaction_id": "T", "amount": "2500000",
                         "currency": "USD"})[0] == "QUARANTINE"
    # classify_batch buckets every row; nothing falls through
    rows = [
        {"transaction_id": "A", "amount": "1", "currency": "USD"},
        {"transaction_id": "B", "amount": "", "currency": "USD"},
        {"transaction_id": "C", "amount": "-1", "currency": "USD"},
    ]
    buckets = classify_batch(rows)
    assert len(buckets["ACCEPT"]) == 1
    assert len(buckets["REJECT"]) == 1
    assert len(buckets["QUARANTINE"]) == 1


# --- Problem 4: stream_totals -------------------------------------------------

def test_04_tallies_in_chunks_with_flat_memory():
    def gen():
        for i in range(2500):
            yield f"USD,{i % 10}.00\n"

    report = stream_totals(gen(), chunk_size=500)
    assert report["completed"] is True
    assert report["rows_seen"] == 2500
    assert report["skipped"] == 0
    assert report["totals"]["USD"] == pytest.approx(sum(i % 10 for i in range(2500)))


def test_04_poison_pill_stops_early_and_reports_incomplete():
    lines = ["USD,10.00\n", "EUR,5.00\n", "__POISON__\n", "USD,999.00\n"]
    report = stream_totals(iter(lines), chunk_size=2)
    assert report["completed"] is False
    assert report["totals"] == {"USD": 10.0, "EUR": 5.0}
    assert report["rows_seen"] == 2


def test_04_malformed_lines_skipped_and_counted():
    lines = ["USD,10.00\n", "\n", "garbage\n", "EUR,notanumber\n",
             "USD,5.00\n"]
    report = stream_totals(iter(lines), chunk_size=10)
    assert report["completed"] is True
    assert report["totals"] == {"USD": 15.0}
    assert report["skipped"] == 3
    assert top_currency(report) == "USD"
    assert top_currency({"totals": {}}) is None


# --- Problem 5: identity / mutability -----------------------------------------

def test_05_tenant_configs_are_independent_objects():
    registry = {}
    register_tenant(registry, "acme", {"batch_size": 500})
    register_tenant(registry, "globex")
    registry["acme"]["columns"].append("debug_flag")
    assert registry["globex"]["columns"] == ["txn_id", "amount", "currency"]
    assert get_batch_size(registry, "acme") == 500
    assert get_batch_size(registry, "globex") == 10_000
    assert not same_object(registry["acme"], registry["globex"])
    assert not same_object(registry["acme"]["columns"],
                           registry["globex"]["columns"])


def test_05_defaults_are_fresh_every_call():
    a = make_default_config()
    b = make_default_config()
    assert a == b
    assert not same_object(a, b)
    assert not same_object(a["columns"], b["columns"])


def test_05_none_means_unset_but_zero_is_real():
    assert resolve_option(None, 10_000) == 10_000
    assert resolve_option(0, 10_000) == 0
    assert resolve_option("", "d") == ""
    registry = {}
    register_tenant(registry, "zero", {"batch_size": 0})
    assert get_batch_size(registry, "zero") == 0  # explicit 0 survives
    assert get_batch_size(registry, "ghost") == 10_000  # unknown tenant


def test_05_dedupe_uses_equality_not_identity():
    rows = [{"id": 1}, {"id": 2}, {"id": 1}, {"id": 3}, {"id": 2}]
    assert dedupe_rows(rows) == [{"id": 1}, {"id": 2}, {"id": 3}]
    a = ["txn_id", "amount"]
    b = ["txn_id", "amount"]
    assert (a == b) is True
    assert same_object(a, b) is False
