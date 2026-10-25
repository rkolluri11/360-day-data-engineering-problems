"""Day 21 tests — every solution must pass before the day is committed.

The suite practices what the day preaches: every test replays
the operation and asserts the replay changed nothing. No timing
bets, no wall-clock, no network — stdlib only.
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_pure_replay import normalize_event
from problem_02_upsert_not_append import apply_batch, upsert
from problem_03_idempotency_key import process_charge, total_charged
from problem_04_atomic_write import write_atomic
from problem_05_replay_safe_pipeline import (
    run_pipeline,
    snapshot,
    total_revenue,
)

RAW = {
    "user_id": "  U-7 ",
    "email": "  Alice@Example.COM ",
    "amount": "19.999",
    "tags": ["b", "a", "b"],
}
CLEAN = {"user_id": "U-7", "email": "alice@example.com", "amount": 20.0, "tags": ["a", "b"]}


# --- Problem 1: pure replay -------------------------------------------------

def test_normalize_reaches_canonical_form():
    assert normalize_event(RAW) == CLEAN


def test_normalize_is_idempotent():
    once = normalize_event(RAW)
    assert normalize_event(once) == once
    assert normalize_event(normalize_event(RAW)) == CLEAN


def test_normalize_does_not_mutate_input():
    event = copy.deepcopy(RAW)
    normalize_event(event)
    assert event == RAW


def test_normalize_is_deterministic():
    assert normalize_event(RAW) == normalize_event(copy.deepcopy(RAW))


def test_normalize_missing_fields_pass_through():
    assert normalize_event({"user_id": "  x "}) == {"user_id": "x"}


# --- Problem 2: upsert, not append -----------------------------------------

def test_upsert_replay_is_noop():
    store = {}
    batch = [("o-1", {"amount": 10.0}), ("o-2", {"amount": 20.0})]
    apply_batch(store, batch)
    before = copy.deepcopy(store)
    apply_batch(store, batch)
    assert store == before
    assert len(store) == 2


def test_upsert_genuine_update_lands():
    store = {}
    upsert(store, "o-1", {"amount": 10.0})
    upsert(store, "o-1", {"amount": 15.0})
    assert store == {"o-1": {"amount": 15.0}}
    assert len(store) == 1


def test_upsert_stores_a_copy_not_an_alias():
    store = {}
    record = {"amount": 10.0}
    upsert(store, "o-1", record)
    record["amount"] = 999.0
    assert store["o-1"]["amount"] == 10.0


# --- Problem 3: idempotency key --------------------------------------------

def test_same_key_replay_returns_original_charge():
    charges = {}
    first = process_charge(charges, "key-1", 50.0)
    replay = process_charge(charges, "key-1", 50.0)
    assert replay == first
    assert replay["charge_id"] == first["charge_id"]
    assert len(charges) == 1
    assert total_charged(charges) == 50.0


def test_same_key_different_amount_does_not_recharge():
    charges = {}
    first = process_charge(charges, "key-1", 50.0)
    replay = process_charge(charges, "key-1", 999.0)
    assert replay["amount"] == 50.0
    assert total_charged(charges) == 50.0


def test_new_key_charges_again():
    charges = {}
    a = process_charge(charges, "key-1", 50.0)
    b = process_charge(charges, "key-2", 30.0)
    assert a["charge_id"] != b["charge_id"]
    assert total_charged(charges) == 80.0


def test_charge_ids_stable_across_replays():
    charges = {}
    process_charge(charges, "key-1", 10.0)
    process_charge(charges, "key-1", 10.0)
    second = process_charge(charges, "key-2", 10.0)
    assert second["charge_id"] == "ch-0002"


# --- Problem 4: atomic write -----------------------------------------------

def test_atomic_write_replay_leaves_identical_bytes(tmp_path):
    target = tmp_path / "out.txt"
    write_atomic(str(target), "hello\n")
    first = target.read_text(encoding="utf-8")
    write_atomic(str(target), "hello\n")
    assert target.read_text(encoding="utf-8") == first == "hello\n"


def test_atomic_write_leaves_no_temp_files(tmp_path):
    target = tmp_path / "out.txt"
    write_atomic(str(target), "data")
    leftovers = [p for p in tmp_path.iterdir() if p.name != "out.txt"]
    assert leftovers == []


def test_atomic_write_replaces_fully_not_appends(tmp_path):
    target = tmp_path / "out.txt"
    write_atomic(str(target), "long content here")
    write_atomic(str(target), "short")
    assert target.read_text(encoding="utf-8") == "short"


def test_atomic_write_returns_path(tmp_path):
    target = tmp_path / "out.txt"
    assert write_atomic(str(target), "x") == str(target)
    assert target.exists()


# --- Problem 5: replay-safe pipeline ---------------------------------------

EVENTS = [
    {"event_id": "e-1", "order_id": "o-1", "amount": 10.0},
    {"event_id": "e-2", "order_id": "o-2", "amount": 20.0},
]


def test_pipeline_full_replay_is_noop():
    store, processed = run_pipeline({}, set(), EVENTS)
    before, n_before = snapshot(store), len(processed)
    run_pipeline(store, processed, EVENTS)
    assert store == before
    assert len(processed) == n_before == 2
    assert total_revenue(store) == 30.0


def test_pipeline_duplicate_event_id_in_one_batch_processed_once():
    events = EVENTS + [{"event_id": "e-1", "order_id": "o-1", "amount": 10.0}]
    store, processed = run_pipeline({}, set(), events)
    assert len(processed) == 2
    assert total_revenue(store) == 30.0


def test_pipeline_correction_updates_once_not_twice():
    store, processed = run_pipeline({}, set(), EVENTS)
    correction = [{"event_id": "e-3", "order_id": "o-1", "amount": 12.0}]
    run_pipeline(store, processed, correction)
    run_pipeline(store, processed, correction)  # replay the correction
    assert store["o-1"]["amount"] == 12.0
    assert len(store) == 2
    assert total_revenue(store) == 32.0


def test_pipeline_revenue_comes_from_store_not_counter():
    store, processed = run_pipeline({}, set(), EVENTS)
    run_pipeline(store, processed, EVENTS)
    run_pipeline(store, processed, EVENTS)
    assert total_revenue(store) == 30.0
    assert len(store) == 2
