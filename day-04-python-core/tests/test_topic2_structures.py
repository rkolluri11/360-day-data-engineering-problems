"""Topic 2 tests — Data Structures (problems 06-10).

Every solution must pass before the day is committed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_06_structures_dedup_scale import dedup_event_ids, find_duplicate_ids
from problem_07_structures_join_lookup import build_lookup, enrich_facts
from problem_08_structures_immutable_keys import composite_key, group_by_key
from problem_09_structures_mutability_trap import (
    collect_errors,
    collect_errors_buggy,
    merge_context,
)
from problem_10_structures_groupby_agg import revenue_rollup, top_region_by_revenue


# --- Problem 6: dedup at scale -------------------------------------------

def test_06_dedup_preserves_first_seen_order():
    assert dedup_event_ids(["c1", "c2", "c1", "c3", "c2"]) == ["c1", "c2", "c3"]


def test_06_dedup_handles_empty_and_all_unique():
    assert dedup_event_ids([]) == []
    assert dedup_event_ids([1, 2, 3]) == [1, 2, 3]


def test_06_find_duplicates_reports_each_once_in_order():
    assert find_duplicate_ids(["a", "b", "a", "a", "c", "b"]) == ["a", "b"]
    assert find_duplicate_ids(["x", "y", "z"]) == []


def test_06_dedup_large_input_matches_set_cardinality():
    big = [f"evt-{i % 500}" for i in range(20_000)]
    unique = dedup_event_ids(big)
    assert len(unique) == 500
    assert unique == [f"evt-{i}" for i in range(500)]  # first-seen order


# --- Problem 7: dict join lookup ------------------------------------------

def test_07_build_lookup_indexes_by_key():
    catalog = [
        {"sku": "p1", "name": "USB Cable"},
        {"sku": "p2", "name": "Keyboard"},
    ]
    lookup = build_lookup(catalog, "sku")
    assert lookup["p1"]["name"] == "USB Cable"
    assert lookup["p2"]["name"] == "Keyboard"


def test_07_enrich_keeps_rows_and_flags_missing_keys():
    lookup = build_lookup([{"sku": "p1", "name": "USB Cable"}], "sku")
    facts = [
        {"order_id": 1, "sku": "p1"},
        {"order_id": 2, "sku": "p9"},  # missing from catalog
    ]
    enriched = enrich_facts(facts, lookup, "sku", default={"name": "UNKNOWN"})
    assert len(enriched) == 2                     # nothing dropped
    assert enriched[0]["dim"]["name"] == "USB Cable"
    assert enriched[1]["dim"]["name"] == "UNKNOWN"  # explicit stamp, not silent
    assert enriched[1]["order_id"] == 2             # fact columns preserved


def test_07_enrich_empty_facts_returns_empty():
    lookup = build_lookup([{"sku": "p1", "name": "USB Cable"}], "sku")
    assert enrich_facts([], lookup, "sku") == []


# --- Problem 8: immutable composite keys -----------------------------------

def test_08_composite_key_is_hashable_tuple():
    key = composite_key("us", "USD")
    assert isinstance(key, tuple)
    assert key == ("us", "USD")
    assert hash(key) == hash(composite_key("us", "USD"))
    assert {key: 1}[key] == 1  # usable as a dict key


def test_08_list_cannot_be_a_dict_key():
    with pytest.raises(TypeError):
        {["us", "USD"]: 1}


def test_08_group_by_key_groups_on_immutable_keys():
    rows = [
        {"region": "us", "currency": "USD", "amount": 10.0},
        {"region": "eu", "currency": "EUR", "amount": 20.0},
        {"region": "us", "currency": "USD", "amount": 5.0},
    ]
    groups = group_by_key(rows, ("region", "currency"))
    assert set(groups.keys()) == {("us", "USD"), ("eu", "EUR")}
    assert all(isinstance(k, tuple) for k in groups)
    assert len(groups[("us", "USD")]) == 2
    assert sum(r["amount"] for r in groups[("us", "USD")]) == 15.0


# --- Problem 9: mutability trap ----------------------------------------------

def test_09_fixed_version_isolated_across_calls():
    assert collect_errors({"id": 1, "status": "bad"}) == [1]
    # a later call starts clean — no ghost from the earlier call
    assert collect_errors({"id": 2, "status": "ok"}) == []


def test_09_fixed_version_accumulates_when_list_passed_explicitly():
    acc = []
    acc = collect_errors({"id": 1, "status": "bad"}, acc)
    acc = collect_errors({"id": 2, "status": "ok"}, acc)
    acc = collect_errors({"id": 3, "status": "bad"}, acc)
    assert acc == [1, 3]


def test_09_buggy_default_is_shared_across_calls():
    # Documents the trap: written to be order-independent.
    before = len(collect_errors_buggy({"id": 9001, "status": "ok"}))
    collect_errors_buggy({"id": 9002, "status": "bad"})
    after = len(collect_errors_buggy({"id": 9003, "status": "ok"}))
    assert after == before + 1  # the bad id leaked into unrelated calls


def test_09_merge_context_never_mutates_inputs():
    base = {"region": "us"}
    extra = {"plan": "pro"}
    merged = merge_context(base, extra)
    assert merged == {"region": "us", "plan": "pro"}
    assert base == {"region": "us"}
    assert extra == {"plan": "pro"}


# --- Problem 10: nested group-by aggregation ----------------------------------

def test_10_revenue_rollup_nests_region_currency_stats():
    rows = [
        {"region": "us", "currency": "USD", "amount": 100.0},
        {"region": "us", "currency": "USD", "amount": 50.0},
        {"region": "eu", "currency": "EUR", "amount": 80.0},
    ]
    rollup = revenue_rollup(rows)
    assert rollup["us"]["USD"] == {"orders": 2, "revenue": 150.0}
    assert rollup["eu"]["EUR"] == {"orders": 1, "revenue": 80.0}


def test_10_rollup_handles_first_seen_keys_without_keyerror():
    # No manual guards needed: brand-new region AND currency just work.
    rollup = revenue_rollup([{"region": "apac", "currency": "JPY", "amount": 5.0}])
    assert rollup == {"apac": {"JPY": {"orders": 1, "revenue": 5.0}}}


def test_10_top_region_by_revenue_sums_currencies():
    rollup = {
        "us": {"USD": {"orders": 2, "revenue": 150.0}},
        "eu": {"EUR": {"orders": 1, "revenue": 80.0},
               "USD": {"orders": 1, "revenue": 20.0}},
    }
    assert top_region_by_revenue(rollup) == ("us", 150.0)
    assert top_region_by_revenue({}) is None
