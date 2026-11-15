"""Day 40 tests: SQL CASE expressions and conditional aggregation.

Same company database as Days 35–39, same 8 orders. All expected
numbers were computed against the seed and checked by hand: tiers
3 large, 3 medium, 1 small, 1 pending; East $54,000, West $27,000,
total $81,000; big orders East 2 ($37,000), West 1 ($15,000);
months Jan $35,000, Feb $37,000, Mar $9,000; East 20000/25000/9000,
West 15000/12000/0; tier sort [1, 3, 5, 2, 6, 8, 4, 7], name sort
[1, 3, 5, 2, 6, 8, 7, 4]; COUNT no-ELSE 3, COUNT ELSE 0 is 8;
backwards ranges give 6 medium, 0 large.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_tier_labels import large_order_ids, tier_counts, tier_of_order
from problem_02_conditional_aggregation import (
    big_counts_by_region,
    big_totals_by_region,
    region_totals,
    total_amount,
)
from problem_03_pivot_months import monthly_totals, pivot_by_region, pivot_total
from problem_04_case_order_by import (
    alpha_tier_order_ids,
    first_by_tier,
    last_by_tier,
    tier_order_ids,
)
from problem_05_count_traps import (
    backwards_range_counts,
    correct_range_counts,
    count_big_else_zero,
    count_big_no_else,
    sum_big_with_else_zero,
)
from seed import create_company_db


# --- Problem 1: CASE labels the row ---
def test_tier_counts_are_three_three_one_one():
    assert tier_counts(create_company_db()) == {
        "large": 3,
        "medium": 3,
        "small": 1,
        "pending": 1,
    }


def test_large_orders_are_one_three_five():
    assert large_order_ids(create_company_db()) == [1, 3, 5]


def test_pending_order_is_order_seven():
    assert tier_of_order(create_company_db(), 7) == "pending"


def test_small_order_is_order_four():
    assert tier_of_order(create_company_db(), 4) == "small"


# --- Problem 2: one pass, both regions ---
def test_region_totals_are_54000_and_27000():
    assert region_totals(create_company_db()) == {"East": 54000, "West": 27000}


def test_total_is_81000():
    assert total_amount(create_company_db()) == 81000


def test_big_orders_split_two_and_one():
    assert big_counts_by_region(create_company_db()) == {"East": 2, "West": 1}


def test_big_dollars_split_37000_and_15000():
    assert big_totals_by_region(create_company_db()) == {"East": 37000, "West": 15000}


# --- Problem 3: the pivot without PIVOT ---
def test_monthly_totals_are_35000_37000_9000():
    assert monthly_totals(create_company_db()) == (35000, 37000, 9000)


def test_pivot_by_region():
    assert pivot_by_region(create_company_db()) == {
        "East": (20000, 25000, 9000),
        "West": (15000, 12000, 0),
    }


def test_pivot_accounts_for_every_dollar():
    assert pivot_total(create_company_db()) == 81000


# --- Problem 4: CASE sorts by meaning ---
def test_tier_sort_puts_25000_first_and_pending_last():
    assert tier_order_ids(create_company_db()) == [1, 3, 5, 2, 6, 8, 4, 7]


def test_name_sort_puts_pending_before_small():
    assert alpha_tier_order_ids(create_company_db()) == [1, 3, 5, 2, 6, 8, 7, 4]


def test_first_and_last_by_tier():
    conn = create_company_db()
    assert first_by_tier(conn) == 1
    assert last_by_tier(conn) == 7


# --- Problem 5: two traps ---
def test_count_without_else_is_three():
    assert count_big_no_else(create_company_db()) == 3


def test_count_with_else_zero_is_eight():
    assert count_big_else_zero(create_company_db()) == 8


def test_sum_with_else_zero_is_still_correct():
    assert sum_big_with_else_zero(create_company_db()) == 52000


def test_backwards_ranges_lose_the_large_bucket():
    assert backwards_range_counts(create_company_db()) == {
        "medium": 6,
        "small": 1,
        "pending": 1,
    }


def test_strictest_first_keeps_all_four_buckets():
    assert correct_range_counts(create_company_db()) == {
        "large": 3,
        "medium": 3,
        "small": 1,
        "pending": 1,
    }
