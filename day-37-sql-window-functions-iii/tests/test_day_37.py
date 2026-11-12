"""Day 37 tests: SQL window functions III (sessionization, gaps-and-islands).

Same company database as Days 35–36. All expected numbers were
computed against the seed and checked by hand: gaps 7/39, 13/27, 5;
five 14-day sessions; David's second session totals NULL, not zero;
six region islands; at a 30-day threshold Frank collapses to one
41-day session worth $29,000.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_gap_between_orders import gaps_between_orders
from problem_02_flag_new_sessions import flag_new_sessions
from problem_03_number_sessions import number_sessions
from problem_04_session_summary import longest_session, session_summary
from problem_05_region_islands import region_islands
from seed import create_company_db


# --- Problem 1: gap in days ---
def test_gaps_between_orders():
    assert gaps_between_orders(create_company_db()) == [
        (6, "2026-01-05", 12000, None, None),
        (6, "2026-01-12", 8000, "2026-01-05", 7),
        (6, "2026-02-20", None, "2026-01-12", 39),
        (7, "2026-01-20", 15000, None, None),
        (7, "2026-02-02", 5000, "2026-01-20", 13),
        (7, "2026-03-01", 9000, "2026-02-02", 27),
        (8, "2026-02-10", 25000, None, None),
        (8, "2026-02-15", 7000, "2026-02-10", 5),
    ]


def test_first_order_gap_is_null_not_zero():
    rows = gaps_between_orders(create_company_db())
    firsts = [r for r in rows if r[3] is None]
    assert len(firsts) == 3
    assert all(r[4] is None for r in firsts)


# --- Problem 2: flag new sessions ---
def test_flag_new_sessions_14_days():
    assert [r[3] for r in flag_new_sessions(create_company_db())] == [
        1, 0, 1,  # David
        1, 0, 1,  # Frank
        1, 0,  # Irene
    ]


def test_flag_new_sessions_30_days_merges_frank():
    rows = flag_new_sessions(create_company_db(), 30)
    frank = [r[3] for r in rows if r[0] == 7]
    assert frank == [1, 0, 0]
    david = [r[3] for r in rows if r[0] == 6]
    assert david == [1, 0, 1]  # 39-day gap still breaks


# --- Problem 3: number the sessions ---
def test_number_sessions():
    assert [(r[0], r[3]) for r in number_sessions(create_company_db())] == [
        (6, 1), (6, 1), (6, 2),
        (7, 1), (7, 1), (7, 2),
        (8, 1), (8, 1),
    ]


def test_five_sessions_total():
    rows = number_sessions(create_company_db())
    assert len({(r[0], r[3]) for r in rows}) == 5


# --- Problem 4: session summary ---
def test_session_summary():
    assert session_summary(create_company_db()) == [
        (6, 1, "2026-01-05", "2026-01-12", 2, 20000, 7),
        (6, 2, "2026-02-20", "2026-02-20", 1, None, 0),
        (7, 1, "2026-01-20", "2026-02-02", 2, 20000, 13),
        (7, 2, "2026-03-01", "2026-03-01", 1, 9000, 0),
        (8, 1, "2026-02-10", "2026-02-15", 2, 32000, 5),
    ]


def test_single_null_order_session_totals_null_not_zero():
    rows = session_summary(create_company_db())
    david_second = [r for r in rows if r[0] == 6 and r[1] == 2][0]
    assert david_second[5] is None


def test_longest_session_is_frank_first():
    assert longest_session(create_company_db()) == (
        7, 1, "2026-01-20", "2026-02-02", 2, 20000, 13,
    )


def test_threshold_decides_the_answer():
    rows = session_summary(create_company_db(), 30)
    assert len(rows) == 4
    frank = [r for r in rows if r[0] == 7][0]
    assert frank == (7, 1, "2026-01-20", "2026-03-01", 3, 29000, 40)


# --- Problem 5: region islands ---
def test_region_islands():
    assert region_islands(create_company_db()) == [
        (6, "East", "2026-01-05", "2026-01-12", 2, 20000),
        (6, "West", "2026-02-20", "2026-02-20", 1, None),
        (7, "West", "2026-01-20", "2026-02-02", 2, 20000),
        (7, "East", "2026-03-01", "2026-03-01", 1, 9000),
        (8, "East", "2026-02-10", "2026-02-10", 1, 25000),
        (8, "West", "2026-02-15", "2026-02-15", 1, 7000),
    ]


def test_six_islands_not_three_regions():
    assert len(region_islands(create_company_db())) == 6


def test_islands_do_not_merge_across_a_gap_in_value():
    rows = region_islands(create_company_db())
    frank_west = [r for r in rows if r[0] == 7 and r[1] == "West"]
    assert len(frank_west) == 1
    irene = [r for r in rows if r[0] == 8]
    assert len(irene) == 2  # East then West: two islands, one session
