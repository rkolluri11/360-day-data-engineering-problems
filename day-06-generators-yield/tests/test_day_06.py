"""Day 6 tests — every solution must pass before the day is committed."""

import inspect
import sys
from itertools import count, islice
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_first_yield import first_n, read_rows
from problem_02_lazy_pipeline import streaming_total
from problem_03_chained_stages import counting_source, pipeline
from problem_04_talking_back import running_stats
from problem_05_streaming_aggregate import streaming_group_sum, top_k


# --- Problem 1: read_rows / first_n ------------------------------------------

def test_01_returns_a_generator_not_a_list():
    assert inspect.isgenerator(read_rows(["a"]))


def test_01_lazy_on_infinite_source():
    def endless():
        i = 0
        while True:
            yield f"  row-{i}  "
            i += 1

    assert first_n(read_rows(endless()), 3) == ["row-0", "row-1", "row-2"]


def test_01_strips_and_drops_empties():
    assert list(read_rows(["  a  ", "", "   ", "b"])) == ["a", "b"]


def test_01_first_n_leaves_rest_paused():
    gen = read_rows(["a", "b", "c", "d"])
    assert first_n(gen, 2) == ["a", "b"]
    assert next(gen) == "c"  # not drained


def test_01_exhausted_generator_raises_stop_iteration():
    gen = read_rows(["only"])
    next(gen)
    with pytest.raises(StopIteration):
        next(gen)


# --- Problem 2: streaming_total ----------------------------------------------

def test_02_basic_total_count_skipped():
    rows = ({"amt": v} for v in ["1.5", "N/A", None, "2.5", "x"])
    assert streaming_total(rows, "amt") == (4.0, 2, 3)


def test_02_streams_without_materializing():
    endless = ({"amt": str(i % 7)} for i in count())
    total, n, skipped = streaming_total(islice(endless, 1_000_000), "amt")
    assert n == 1_000_000 and skipped == 0
    assert total == pytest.approx(sum(i % 7 for i in range(1_000_000)))


def test_02_missing_key_counts_as_skipped():
    rows = ({"other": "1"} for _ in range(3))
    assert streaming_total(rows, "amt") == (0.0, 0, 3)


def test_02_single_use_generator_is_empty_second_time():
    rows = ({"amt": "5"} for _ in range(2))
    assert streaming_total(rows, "amt")[1] == 2
    assert streaming_total(rows, "amt") == (0.0, 0, 0)  # exhausted: documented


# --- Problem 3: pipeline / counting_source ------------------------------------

def test_03_stages_apply_in_order():
    def double(items):
        return (x * 2 for x in items)

    def add_one(items):
        return (x + 1 for x in items)

    assert list(pipeline(iter([1, 2, 3]), double, add_one)) == [3, 5, 7]


def test_03_pull_based_laziness():
    src, pulled = counting_source(1_000_000)
    result = pipeline(src, lambda it: (x * 2 for x in it))
    assert list(islice(result, 4)) == [0, 2, 4, 6]
    assert pulled[0] == 4  # upstream did no extra work


def test_03_no_stages_is_identity():
    assert list(pipeline(iter([1, 2]), )) == [1, 2]


def test_03_filter_stage_short_circuits_source():
    src, pulled = counting_source(1_000_000)

    def evens(items):
        for x in items:
            if x % 2 == 0:
                yield x

    assert list(islice(pipeline(src, evens), 3)) == [0, 2, 4]
    assert pulled[0] == 5


# --- Problem 4: running_stats --------------------------------------------------

def test_04_primed_first_send_works():
    stats, _ = running_stats()
    assert stats.send(10) == (1, 10.0)  # no manual next() needed


def test_04_running_mean():
    stats, _ = running_stats()
    stats.send(10)
    assert stats.send(20) == (2, 15.0)
    assert stats.send(30) == (3, 20.0)


def test_04_non_numeric_skipped_not_crashed():
    stats, _ = running_stats()
    stats.send(10)
    assert stats.send("oops") == (1, 10.0)
    assert stats.send(None) == (1, 10.0)


def test_04_close_flushes_final_triple():
    stats, final = running_stats()
    stats.send(10)
    stats.send(20)
    stats.send("bad")
    stats.close()
    assert final == [(2, 15.0, 1)]


def test_04_send_after_close_raises_stop_iteration():
    stats, _ = running_stats()
    stats.close()
    with pytest.raises(StopIteration):
        stats.send(1)


# --- Problem 5: streaming_group_sum --------------------------------------------

def test_05_group_sums_correct():
    rows = (r for r in [
        {"user": "a", "amt": "10"},
        {"user": "b", "amt": "5"},
        {"user": "a", "amt": "2.5"},
    ])
    totals, seen, skipped = streaming_group_sum(rows, "user", "amt")
    assert totals == {"a": 12.5, "b": 5.0}
    assert (seen, skipped) == (3, 0)


def test_05_bad_rows_skipped_with_counts():
    rows = (r for r in [
        {"user": "a", "amt": "10"},
        {"user": "a"},                    # missing value
        {"user": "b", "amt": "junk"},     # unparseable
        {"amt": "3"},                     # missing key
        {"user": None, "amt": "3"},        # null key
    ])
    totals, seen, skipped = streaming_group_sum(rows, "user", "amt")
    assert totals == {"a": 10.0}
    assert (seen, skipped) == (5, 4)


def test_05_streams_large_source():
    def fake_events(n):
        for i in range(n):
            yield {"user": f"u{i % 1_000}", "amt": str(i % 10)}

    totals, seen, skipped = streaming_group_sum(fake_events(200_000), "user", "amt")
    assert seen == 200_000 and skipped == 0 and len(totals) == 1_000
    # every user appears 200 times; each residue class sums identically
    assert totals["u7"] == pytest.approx(200 * 7)


def test_05_top_k_descending():
    assert top_k({"a": 10.0, "b": 50.0, "c": 30.0}, 2) == [("b", 50.0), ("c", 30.0)]
