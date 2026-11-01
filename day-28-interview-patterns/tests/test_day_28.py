"""Day 28 tests — Interview day: hashmaps + sliding window patterns.

Stdlib only, no network, no sleeping. Each problem is tested on its
documented contract, including the edge cases named in its docstring.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from problem_01_longest_unique_window import longest_unique_window
from problem_02_sliding_window_aggregate import (
    moving_averages,
    sliding_window_max_sum,
)
from problem_03_frequency_tracker import FrequencyTracker
from problem_04_windowed_dedup import WindowDeduper
from problem_05_minimum_window_cover import minimum_window_cover


# --- Problem 1: longest unique window -------------------------------------

def test_leetcode_anchor_abcabcbb():
    assert longest_unique_window("abcabcbb") == (3, "abc")


def test_repeated_char_jumps_left_edge_not_restart():
    # "abba": after the second 'b', left jumps past the first 'b',
    # leaving "ba" — a restart-from-scratch scan would report "ab".
    assert longest_unique_window("abba") == (2, "ab")


def test_all_unique_and_all_same():
    assert longest_unique_window("abcdef") == (6, "abcdef")
    assert longest_unique_window("aaaa") == (1, "a")


def test_empty_and_non_string():
    assert longest_unique_window("") == (0, "")
    with pytest.raises(TypeError):
        longest_unique_window(123)


# --- Problem 2: sliding window aggregates ---------------------------------

def test_max_sum_window():
    assert sliding_window_max_sum([1, 4, 2, 10, 23, 3, 1, 0, 20], 4) == 39


def test_moving_averages():
    assert moving_averages([1, 3, 5, 7, 9], 3) == [3.0, 5.0, 7.0]
    assert moving_averages([10, 20, 30], 1) == [10.0, 20.0, 30.0]
    assert moving_averages([2, 4], 2) == [3.0]


def test_window_validation():
    with pytest.raises(ValueError):
        sliding_window_max_sum([], 1)
    with pytest.raises(ValueError):
        sliding_window_max_sum([1, 2], 0)
    with pytest.raises(ValueError):
        sliding_window_max_sum([1, 2], 3)
    with pytest.raises(ValueError):
        moving_averages([1, 2], -1)


# --- Problem 3: frequency tracker ------------------------------------------

def test_first_unique_arrival_order():
    tracker = FrequencyTracker()
    for item in ["click", "purchase", "click", "view"]:
        tracker.add(item)
    assert tracker.counts() == {"click": 2, "purchase": 1, "view": 1}
    assert tracker.first_unique() == "purchase"


def test_first_unique_none_when_all_repeat():
    tracker = FrequencyTracker()
    for item in ["a", "a", "b", "b"]:
        tracker.add(item)
    assert tracker.first_unique() is None
    assert FrequencyTracker().first_unique() is None


def test_top_k_count_then_first_seen_tiebreak():
    tracker = FrequencyTracker()
    for item in ["b", "a", "b", "a", "c"]:
        tracker.add(item)
    # b and a tie at 2; b arrived first.
    assert tracker.top_k(2) == ["b", "a"]
    assert tracker.top_k(0) == []
    assert tracker.top_k(99) == ["b", "a", "c"]


def test_counts_copy_cannot_corrupt_state():
    tracker = FrequencyTracker()
    tracker.add("x")
    copy = tracker.counts()
    copy["x"] = 999
    assert tracker.counts() == {"x": 1}


# --- Problem 4: windowed dedup ---------------------------------------------

def test_duplicate_inside_window_dropped():
    deduper = WindowDeduper(3)
    assert [deduper.offer(x) for x in ["a", "b", "a"]] == [True, True, False]
    assert deduper.accepted() == ["a", "b"]


def test_repeat_after_window_slides_passes_again():
    deduper = WindowDeduper(3)
    for item in ["a", "b", "c", "d"]:
        deduper.offer(item)
    # Window of accepted items is now [b, c, d]; "a" has slid out.
    assert deduper.offer("a") is True
    assert deduper.accepted() == ["a", "b", "c", "d", "a"]


def test_dropped_retry_does_not_refresh_window():
    deduper = WindowDeduper(2)
    deduper.offer("a")
    deduper.offer("b")
    assert deduper.offer("a") is False  # dropped, window still [a, b]
    deduper.offer("c")  # evicts "a"
    assert deduper.offer("a") is True


def test_window_size_validation():
    with pytest.raises(ValueError):
        WindowDeduper(0)
    with pytest.raises(ValueError):
        WindowDeduper(-2)


# --- Problem 5: minimum window cover ---------------------------------------

def test_shortest_cover_with_extras():
    events = ["login", "noise", "checkout", "login", "receipt"]
    assert minimum_window_cover(events, {"login", "checkout", "receipt"}) == (
        2, 4, ["checkout", "login", "receipt"],
    )


def test_cover_is_tight_not_first_occurrence():
    # Shortest is the tail ["b", "a"], not the span from the first "a".
    assert minimum_window_cover(["a", "x", "b", "a"], {"a", "b"}) == (
        2, 3, ["b", "a"],
    )


def test_impossible_and_empty_requirement():
    assert minimum_window_cover(["a", "b"], {"a", "c"}) is None
    assert minimum_window_cover([], {"a"}) is None
    assert minimum_window_cover(["a"], set()) == (0, -1, [])
