"""Day 7 tests — every solution must pass before the day is committed."""

import sys
from collections import Counter
from itertools import count, islice
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_first_comprehension import big_amounts, clean_emails
from problem_02_dedup_index import dedup_by_key, distinct_values
from problem_03_counter_rollup import status_counts, top_k_statuses
from problem_04_defaultdict_groups import group_by, sum_by
from problem_05_streaming_rollup import (
    sampled_status_counts,
    streaming_user_totals,
)


# --- Problem 1: clean_emails / big_amounts -----------------------------------

def test_01_strips_lowercases_and_drops_empties():
    raw = ["  Ada@Mail.com ", "", "   ", "bob@mail.com", None, 42]
    assert clean_emails(raw) == ["ada@mail.com", "bob@mail.com"]


def test_01_keeps_duplicates_and_order():
    assert clean_emails(["A@x.com", "a@X.com "]) == ["a@x.com", "a@x.com"]


def test_01_big_amounts_filters_on_threshold():
    rows = [{"amt": 5}, {"amt": 500}, {"amt": 50}]
    assert big_amounts(rows, 50) == [500, 50]


def test_01_big_amounts_empty_on_no_match():
    assert big_amounts([{"amt": 1}], 100) == []


# --- Problem 2: dedup_by_key / distinct_values -------------------------------

def test_02_later_rows_win():
    rows = [{"email": "a@x.com", "v": 1},
            {"email": "b@x.com", "v": 2},
            {"email": "a@x.com", "v": 3}]
    dedup = dedup_by_key(rows, "email")
    assert dedup["a@x.com"]["v"] == 3
    assert len(dedup) == 2


def test_02_no_duplicates_keeps_all():
    rows = [{"id": 1}, {"id": 2}]
    assert dedup_by_key(rows, "id") == {1: {"id": 1}, 2: {"id": 2}}


def test_02_distinct_values_returns_set():
    rows = [{"s": "ok"}, {"s": "fail"}, {"s": "ok"}]
    assert distinct_values(rows, "s") == {"ok", "fail"}


def test_02_distinct_values_single_value():
    assert distinct_values([{"s": "ok"}, {"s": "ok"}], "s") == {"ok"}


# --- Problem 3: status_counts / top_k_statuses --------------------------------

def test_03_returns_a_counter():
    events = [{"status": "ok"}, {"status": "fail"}]
    counts = status_counts(events)
    assert isinstance(counts, Counter)
    assert counts == Counter({"ok": 1, "fail": 1})


def test_03_missing_key_reads_zero_not_keyerror():
    assert status_counts([{"status": "ok"}])["never-seen"] == 0


def test_03_works_on_a_generator_without_materializing():
    def endless():
        i = 0
        while True:
            yield {"status": "ok" if i % 2 else "fail"}
            i += 1

    counts = status_counts(islice(endless(), 100))
    assert counts == Counter({"ok": 50, "fail": 50})


def test_03_top_k_ordering_and_shape():
    events = [{"status": s} for s in
              ["ok"] * 5 + ["retry"] * 2 + ["fail"]]
    assert top_k_statuses(events, 2) == [("ok", 5), ("retry", 2)]


# --- Problem 4: group_by / sum_by --------------------------------------------

def test_04_groups_rows_by_key():
    rows = [{"u": "a", "x": 1}, {"u": "b", "x": 2}, {"u": "a", "x": 3}]
    groups = group_by(rows, "u")
    assert set(groups) == {"a", "b"}
    assert [r["x"] for r in groups["a"]] == [1, 3]


def test_04_returns_plain_dict_not_defaultdict():
    assert type(group_by([{"u": "a"}], "u")) is dict


def test_04_sum_by_totals_per_key():
    rows = [{"u": "a", "amt": 10.0}, {"u": "b", "amt": 5.0},
            {"u": "a", "amt": 7.5}]
    assert sum_by(rows, "u", "amt") == {"a": 17.5, "b": 5.0}


def test_04_sum_by_missing_field_counts_zero():
    rows = [{"u": "a", "amt": 10.0}, {"u": "a"}]
    assert sum_by(rows, "u", "amt") == {"a": 10.0}


# --- Problem 5: sampled_status_counts / streaming_user_totals -----------------

def test_05_samples_n_from_infinite_source():
    def endless():
        i = 0
        while True:
            yield "ok" if i % 10 else "fail"
            i += 1

    counts = sampled_status_counts(endless(), 20)
    assert counts == Counter({"ok": 18, "fail": 2})


def test_05_pulls_at_most_n_items():
    pulled = []

    def counting():
        for i in count():
            pulled.append(i)
            yield "ok"

    sampled_status_counts(counting(), 7)
    assert pulled == list(range(7))  # never touched item 8


def test_05_streaming_user_totals_over_generator():
    def pairs():
        yield ("ada", 10.0)
        yield ("bob", 5.0)
        yield ("ada", 7.5)

    assert streaming_user_totals(pairs()) == {"ada": 17.5, "bob": 5.0}


def test_05_handles_none_amounts_as_zero():
    def pairs():
        yield ("ada", None)
        yield ("ada", 3.0)

    assert streaming_user_totals(pairs()) == {"ada": 3.0}
