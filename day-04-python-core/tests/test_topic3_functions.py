"""Day 4 Topic 3 tests — Functions. Every solution must pass before review."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_11_functions_flexible_steps import (
    call_step, run_all, dedupe, cap_amount, tag_vip,
)
from problem_12_functions_mutable_default import ingest, quarantine
from problem_13_functions_loop_closures import (
    build_checks, make_check, validate,
)
from problem_14_functions_filter_predicates import (
    all_of, any_of, build_predicate, flag,
)
from problem_15_functions_pure_scope import (
    convert_batch, run_fx, summarize,
)


# --- Problem 11: *args/**kwargs flexible dispatch --------------------------

def test_11_call_step_forwards_new_knobs_untouched():
    rows = [{"amount": 99}]
    out = call_step(cap_amount, rows, 50, currency="EUR")
    assert out[0]["amount"] == 50
    assert out[0]["currency"] == "EUR"


def test_11_run_all_broadcasts_shared_knobs_only_where_accepted():
    rows = [{"customer": "a1", "amount": 500}]
    # dry_run is accepted by cap_amount only; dedupe never sees it
    # (no "unexpected keyword argument" crash on steps that lack it).
    out = run_all([dedupe, tag_vip], rows, {"a1"}, dry_run=True)
    assert out == [{"customer": "a1", "amount": 500, "tags": ["vip"]}]
    # ...while cap_amount does receive and honor it.
    report = call_step(cap_amount, rows, 100, dry_run=True)
    assert report["would_change"] == 1
    assert report["rows"] == rows


def test_11_run_all_without_shared_knobs_runs_pipeline():
    rows = [
        {"customer": "a1", "amount": 500},
        {"customer": "a1", "amount": 500},
    ]
    out = run_all([dedupe, tag_vip], rows, vip_ids={"a1"})
    assert len(out) == 1                  # duplicate removed
    assert out[0]["tags"] == ["vip"]      # tagged


# --- Problem 12: mutable default trap --------------------------------------

def test_12_ingest_audit_does_not_leak_between_files():
    _, audit_a = ingest("2026-10-06-a.csv")
    _, audit_b = ingest("2026-10-06-b.csv")
    assert len(audit_a) == 1
    assert len(audit_b) == 0             # would be 1 with shared default


def test_12_retry_of_same_file_stays_idempotent():
    _, first = ingest("2026-10-06-a.csv")
    _, retry = ingest("2026-10-06-a.csv")
    assert len(first) == len(retry) == 1  # no double-append


def test_12_quarantine_isolated_unless_list_shared_explicitly():
    assert len(quarantine({"id": 1})) == 1
    assert len(quarantine({"id": 2})) == 1   # fresh list, not 2
    shared = []
    quarantine({"id": 3}, shared)
    quarantine({"id": 4}, shared)
    assert len(shared) == 2                 # explicit sharing still works


# --- Problem 13: loop closures / late binding -------------------------------

def test_13_each_checker_validates_its_own_column():
    specs = [
        {"name": "amount", "rule": "positive"},
        {"name": "currency", "rule": "not_null"},
    ]
    checks = build_checks(specs)
    assert checks[0]({"amount": -5, "currency": "USD"}) is False
    assert checks[0]({"amount": 10, "currency": None}) is True   # not its col
    assert checks[1]({"amount": 10, "currency": None}) is False
    assert checks[1]({"amount": -5, "currency": "USD"}) is True  # not its col


def test_13_validate_catches_bad_amount_not_just_last_column():
    specs = [
        {"name": "amount", "rule": "positive"},
        {"name": "currency", "rule": "not_null"},
        {"name": "event_ts", "rule": "not_null"},
    ]
    checks = build_checks(specs)
    rows = [{"amount": -5, "currency": "USD", "event_ts": "2026-10-06"}]
    good, bad = validate(rows, checks)
    assert good == [] and len(bad) == 1
    assert any("amount" in name for name in bad[0]["_failed"])


def test_13_make_check_unknown_rule_raises():
    with pytest.raises(ValueError):
        make_check("amount", "quantum")


# --- Problem 14: lambda + higher-order filter predicates --------------------

def test_14_build_predicate_all_mode():
    rules = [
        {"field": "amount", "op": "gt", "value": 1000},
        {"field": "tier", "op": "eq", "value": "vip"},
    ]
    pred, desc = build_predicate(rules)
    assert pred({"amount": 5000, "tier": "vip"}) is True
    assert pred({"amount": 5000, "tier": "basic"}) is False
    assert "amount gt 1000" in desc      # audit-ready description


def test_14_any_mode_and_combinators():
    is_big = lambda r: r["amount"] > 1000
    is_vip = lambda r: r["tier"] == "vip"
    assert any_of(is_big, is_vip)({"amount": 5, "tier": "vip"}) is True
    assert all_of(is_big, is_vip)({"amount": 5, "tier": "vip"}) is False
    flagged, audit = flag(
        [{"id": 1, "amount": 5, "tier": "vip"}],
        [{"field": "tier", "op": "eq", "value": "vip"}], mode="any")
    assert [r["id"] for r in flagged] == [1]
    assert audit["scanned"] == 1 and audit["flagged_count"] == 1


def test_14_empty_rules_match_all_and_bad_op_raises():
    pred, desc = build_predicate([])
    assert pred({"anything": 1}) is True
    assert "match all" in desc
    with pytest.raises(ValueError):
        build_predicate([{"field": "a", "op": "approx", "value": 1}])


# --- Problem 15: scope & pure functions --------------------------------------

def test_15_convert_batch_is_deterministic_and_pure():
    rows = [{"id": 1, "amount_usd": 100}, {"id": 2, "amount_usd": -5}]
    c1, e1 = convert_batch(rows, 1.08)
    c2, e2 = convert_batch(rows, 1.08)
    assert (c1, e1) == (c2, e2)           # rerun-proof
    assert c1[0]["amount_eur"] == 108.0
    assert len(e1) == 1 and e1[0]["id"] == 2
    assert rows[0].keys() == {"id", "amount_usd"}  # input not mutated


def test_15_summarize_totals_converted_rows():
    converted, _ = convert_batch(
        [{"id": 1, "amount_usd": 100}, {"id": 2, "amount_usd": 200}], 1.5)
    assert summarize(converted) == {"rows": 2, "total_eur": 450.0}


def test_15_run_fx_fetches_rate_once_per_batch():
    calls = {"n": 0}

    def fake_source():
        calls["n"] += 1
        return 2.0

    out = run_fx([{"id": 1, "amount_usd": 50}], fake_source)
    assert calls["n"] == 1                # no mid-batch refresh
    assert out["rate_used"] == 2.0
    assert out["converted"][0]["amount_eur"] == 100.0
    assert out["summary"]["rows"] == 1
