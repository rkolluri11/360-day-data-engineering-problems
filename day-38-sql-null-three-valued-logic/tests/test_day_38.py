"""Day 38 tests: SQL NULL handling and three-valued logic.

Same company database as Days 35–37. All expected numbers were
computed against the seed and checked by hand: 8 orders, 7 priced,
SUM $81,000, AVG $11,571.43 priced / $10,125 with COALESCE; David
3 orders, 2 priced, $20,000; 5 people with no manager; NOT IN
returns 0 rows, NOT EXISTS returns the real 9 non-managers.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_is_null import equals_null_count, null_amount_orders, null_managers
from problem_02_three_valued_logic import truth_table
from problem_03_where_drops_unknown import where_counts
from problem_04_aggregates_skip_nulls import (
    order_aggregates,
    per_employee_aggregates,
    single_null_total,
)
from problem_05_not_in_trap import (
    NON_MANAGERS,
    not_exists_non_managers,
    not_in_count,
    not_in_fixed,
)
from seed import create_company_db


# --- Problem 1: IS NULL, never = NULL ---
def test_null_amount_order_is_davids_pending_quote():
    assert null_amount_orders(create_company_db()) == [
        (7, 6, "West", None, "2026-02-20")
    ]


def test_equals_null_matches_nothing():
    assert equals_null_count(create_company_db()) == 0


def test_five_people_have_no_manager():
    assert null_managers(create_company_db()) == [
        "Grace Liu",
        "Irene Novak",
        "Karen White",
        "Mia Brown",
        "Nina Patel",
    ]


# --- Problem 2: three-valued logic ---
def test_truth_table():
    assert dict(truth_table(create_company_db())) == {
        "NULL = NULL": None,
        "NULL <> 1": None,
        "NOT NULL": None,
        "NULL AND 0": 0,
        "NULL AND 1": None,
        "NULL OR 0": None,
        "NULL OR 1": 1,
    }


def test_unknown_and_false_is_false_not_unknown():
    table = dict(truth_table(create_company_db()))
    assert table["NULL AND 0"] == 0
    assert table["NULL OR 1"] == 1


# --- Problem 3: WHERE drops UNKNOWN ---
def test_where_counts():
    assert where_counts(create_company_db()) == {
        "amount_gt_10000": 3,
        "not_amount_gt_10000": 4,
        "amount_ne_12000": 6,
        "amount_is_null": 1,
        "total_orders": 8,
    }


def test_filter_and_complement_do_not_add_up_to_total():
    counts = where_counts(create_company_db())
    # 3 + 4 = 7, not 8: the NULL row falls out of both sides.
    assert (
        counts["amount_gt_10000"] + counts["not_amount_gt_10000"]
        == counts["total_orders"] - counts["amount_is_null"]
    )


# --- Problem 4: aggregates skip NULLs ---
def test_order_aggregates():
    total, priced, total_sum, avg_priced, avg_all = order_aggregates(
        create_company_db()
    )
    assert (total, priced, total_sum) == (8, 7, 81000)
    assert avg_priced == pytest.approx(11571.42857142857)
    assert avg_all == pytest.approx(10125.0)


def test_per_employee_aggregates():
    assert per_employee_aggregates(create_company_db()) == [
        (6, 3, 2, 20000, 10000.0),  # David: 3 orders, 2 priced
        (7, 3, 3, 29000, pytest.approx(9666.666666666666)),
        (8, 2, 2, 32000, 16000.0),
    ]


def test_sum_over_only_null_is_null_not_zero():
    assert single_null_total(create_company_db()) is None


# --- Problem 5: NOT IN trap ---
def test_not_in_returns_nothing():
    assert not_in_count(create_company_db()) == 0


def test_not_in_fixed_returns_nine():
    assert not_in_fixed(create_company_db()) == NON_MANAGERS


def test_not_exists_returns_same_nine():
    assert not_exists_non_managers(create_company_db()) == NON_MANAGERS


def test_non_managers_are_nine_not_thirteen():
    assert len(NON_MANAGERS) == 9
