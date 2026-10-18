"""Day 14 tests — every solution must pass before the day is committed.

The suite practices what the day preaches: real @pytest.fixture factories
and @pytest.mark.parametrize tables, testing transforms the way the
calendar row demands ("mirrors the repo's pytest convention").
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_fixture_factory import dirty_row, fresh_batch, upper_status
from problem_02_parametrize_the_boundary import parse_amount
from problem_03_assert_like_an_engineer import (
    assert_null_rate,
    assert_schema,
    assert_unique,
    dedupe_by_key,
    null_rate,
)
from problem_04_quarantine_not_crash import clean_batch
from problem_05_end_to_end_stage import run_stage


# --- shared fixtures: the day's own topic, in use ----------------------------

@pytest.fixture
def batch():
    """A fresh dirty batch for every test that asks for it."""
    return fresh_batch()


@pytest.fixture
def mixed_batch():
    """Good rows plus one of every failure mode problem 4 routes."""
    return [
        dirty_row(order_id="o-1", amount="10.00"),
        dirty_row(order_id="o-2", amount="$1,234.56"),
        dirty_row(order_id="", amount="5.00"),            # missing order_id
        dirty_row(order_id="o-4", amount="abc"),          # bad amount
        dirty_row(order_id="o-5", amount=None),           # missing amount
        dirty_row(order_id="o-6", amount="-3.00"),        # negative amount
    ]


# --- Problem 1: fixture factory -----------------------------------------------

def test_01_factory_returns_fresh_objects_every_call():
    first = fresh_batch()
    first.append(dirty_row(order_id="o-x"))
    first[0]["status"] = "mangled"
    second = fresh_batch()
    assert len(second) == 3
    assert all(r["status"] == "paid" for r in second)


def test_01_overrides_set_only_named_fields():
    row = dirty_row(order_id="o-9")
    assert row == {"order_id": "o-9", "amount": "1,234.56", "status": "paid"}


def test_01_fixture_batch_is_independent_per_test(batch):
    batch.append(dirty_row(order_id="o-x"))  # mutate freely...
    assert len(batch) == 4


def test_01_fixture_batch_still_fresh_here(batch):
    assert len(batch) == 3  # ...because this test got its own tray


def test_01_upper_status_normalizes(batch):
    out = [upper_status(r) for r in batch]
    assert all(r["status"] == "PAID" for r in out)
    assert all(r["status"] == "paid" for r in batch)  # input untouched


# --- Problem 2: parametrize the boundary ---------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("10.00", 10.0),
    ("1,234.56", 1234.56),
    ("$12.50", 12.5),
    ("(45.00)", -45.0),
    ("($1,000.00)", -1000.0),
    ("1e3", 1000.0),
    ("-3.25", -3.25),
    ("  7.50  ", 7.5),
    (None, None),
    ("", None),
    ("   ", None),
])
def test_02_parse_amount_table(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "12.34.56", "12a", "--5", "("])
def test_02_parse_amount_rejects_garbage(raw):
    with pytest.raises(ValueError, match="bad amount"):
        parse_amount(raw)


def test_02_none_is_absent_not_zero():
    assert parse_amount(None) is None
    assert parse_amount(None) != 0.0


# --- Problem 3: assert like an engineer ----------------------------------------

def test_03_dedupe_keeps_first_occurrence():
    rows = [dirty_row(order_id="o-1"), dirty_row(order_id="o-1"),
            dirty_row(order_id="o-2")]
    out = dedupe_by_key(rows, "order_id")
    assert [r["order_id"] for r in out] == ["o-1", "o-2"]


def test_03_assert_unique_names_dupes_and_rows():
    rows = [dirty_row(order_id="o-7"), dirty_row(order_id="o-7")]
    with pytest.raises(AssertionError, match="o-7.*rows \\[0, 1\\]"):
        assert_unique(rows, "order_id")


def test_03_assert_unique_passes_on_clean(batch):
    assert assert_unique(batch, "order_id") is True


def test_03_null_rate_counts_none_and_blank():
    rows = [dirty_row(amount=None), dirty_row(amount="  "),
            dirty_row(amount="1.0"), dirty_row(amount="2.0")]
    assert null_rate(rows, "amount") == 0.5


def test_03_assert_null_rate_threshold():
    rows = [dirty_row(amount=None), dirty_row(amount="1.0")]
    assert assert_null_rate(rows, "amount", 0.5) is True
    with pytest.raises(AssertionError, match="0.50.*above allowed 0.10"):
        assert_null_rate(rows, "amount", 0.10)


def test_03_assert_null_rate_empty_batch_raises():
    with pytest.raises(AssertionError, match="no rows"):
        assert_null_rate([], "amount", 1.0)


def test_03_assert_schema_checks_presence_not_truthiness():
    rows = [{"order_id": "o-1", "amount": None}]  # null value, key present: fine
    assert assert_schema(rows, ["order_id", "amount"]) is True
    with pytest.raises(AssertionError, match="row 0 missing \\['amount'\\]"):
        assert_schema([{"order_id": "o-1"}], ["order_id", "amount"])


# --- Problem 4: quarantine, don't crash ----------------------------------------

def test_04_good_rows_parse_and_bad_rows_route(mixed_batch):
    clean, quarantined = clean_batch(mixed_batch)
    assert [r["order_id"] for r in clean] == ["o-1", "o-2"]
    assert clean[1]["amount"] == 1234.56  # normalized to float, once
    assert [q["_reason"] for q in quarantined] == [
        "missing:order_id",
        "bad_amount:'abc'",
        "missing:amount",
        "negative_amount:-3.0",
    ]


def test_04_never_raises_on_row_data():
    hostile = [
        {},
        {"order_id": None, "amount": None},
        {"order_id": "o-1", "amount": {"nested": "dict"}},
        {"order_id": "o-2", "amount": ["a", "list"]},
    ]
    clean, quarantined = clean_batch(hostile)  # must not raise
    assert len(clean) + len(quarantined) == len(hostile)


def test_04_input_batch_is_never_mutated(mixed_batch):
    snapshot = [dict(r) for r in mixed_batch]
    clean_batch(mixed_batch)
    assert mixed_batch == snapshot


def test_04_quarantine_carries_the_evidence(mixed_batch):
    _, quarantined = clean_batch(mixed_batch)
    by_reason = {q["_reason"]: q["_row"] for q in quarantined}
    assert by_reason["bad_amount:'abc'"]["order_id"] == "o-4"


# --- Problem 5: end-to-end stage ------------------------------------------------

DIRTY_CSV = (
    "order_id,amount,status\n"
    "o-1,10.00,paid\n"
    "o-2,\"$1,234.56\",paid\n"
    "o-3,abc,paid\n"
    ",5.00,paid\n"
)


def _run(tmp_path):
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    q_csv = tmp_path / "quarantine.csv"
    in_csv.write_text(DIRTY_CSV)
    stats = run_stage(str(in_csv), str(out_csv), str(q_csv))
    return stats, out_csv, q_csv


def test_05_stage_stats_account_for_every_row(tmp_path):
    stats, _, _ = _run(tmp_path)
    assert stats == {"in": 4, "clean": 2, "quarantined": 2}
    assert stats["in"] == stats["clean"] + stats["quarantined"]


def test_05_clean_csv_holds_parsed_amounts(tmp_path):
    _, out_csv, _ = _run(tmp_path)
    with open(out_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert [(r["order_id"], r["amount"]) for r in rows] == [
        ("o-1", "10.0"), ("o-2", "1234.56")]
    float(rows[0]["amount"])  # parses as a real number, not a money string


def test_05_quarantine_csv_carries_reasons(tmp_path):
    _, _, q_csv = _run(tmp_path)
    with open(q_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert sorted(r["_reason"] for r in rows) == [
        "bad_amount:'abc'", "missing:order_id"]


def test_05_stage_is_idempotent(tmp_path):
    stats1, out1, q1 = _run(tmp_path)
    in_csv = tmp_path / "in.csv"
    stats2 = run_stage(str(in_csv), str(out1), str(q1))
    assert stats2 == stats1
    with open(out1, newline="") as f:
        rerun_rows = list(csv.DictReader(f))
    assert len(rerun_rows) == 2  # a retry never double-counts
