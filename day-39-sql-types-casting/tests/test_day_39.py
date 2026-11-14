"""Day 39 tests: SQL data types and casting pitfalls.

Same company database as Days 35–38, plus the staging tables where
the types go wrong. All expected numbers were computed against the
seed and checked by hand: text sort puts 9 on top, the real top is
100; padded codes join 0 rows as text and 13 as integers; the text
filter returns 7 rows, the CAST filter 3; the five silent CASTs sum
to 12,024; the plain salary lookup SEARCHes the index and the CAST
one SCANs; SUM/COUNT truncates to 11,571 while AVG is 11,571.43.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_text_sorts import cast_order, cast_top_score, text_order, text_top_score
from problem_02_padded_codes import (
    join_cast_count,
    join_raw_count,
    join_to_employees_count,
)
from problem_03_text_filter import cast_filter_ids, text_filter_ids
from problem_04_silent_cast import cast_real_value, cast_sum, cast_values
from problem_05_cast_kills_index import (
    cast_salary_uses_index,
    int_division_average,
    plain_salary_uses_index,
    real_average,
)
from seed import create_company_db


# --- Problem 1: text sorts like text ---
def test_text_sort_puts_nine_on_top():
    assert text_top_score(create_company_db()) == "Priya"


def test_text_order_is_lexicographic():
    assert text_order(create_company_db()) == [
        "Priya",
        "Tara",
        "Sam",
        "Rosa",
        "Quinn",
    ]


def test_cast_sort_puts_hundred_on_top():
    assert cast_top_score(create_company_db()) == "Rosa"


def test_cast_order_is_numeric():
    assert cast_order(create_company_db()) == [
        "Rosa",
        "Sam",
        "Quinn",
        "Priya",
        "Tara",
    ]


# --- Problem 2: padded codes don't join ---
def test_padded_codes_join_zero_rows_as_text():
    assert join_raw_count(create_company_db()) == 0


def test_padded_codes_join_all_thirteen_as_integers():
    assert join_cast_count(create_company_db()) == 13


def test_cast_join_matches_all_employees():
    assert join_to_employees_count(create_company_db()) == 13


# --- Problem 3: a text filter lies ---
def test_text_filter_returns_seven_rows():
    assert text_filter_ids(create_company_db()) == [1, 2, 3, 4, 5, 6, 8]


def test_cast_filter_returns_the_real_three():
    assert cast_filter_ids(create_company_db()) == [1, 3, 5]


def test_text_filter_includes_sub_10000_orders():
    ids = text_filter_ids(create_company_db())
    assert 4 in ids  # Frank's $5,000 order passes a text filter


# --- Problem 4: CAST is silent ---
def test_cast_values():
    assert cast_values(create_company_db()) == [
        ("12000", 12000),
        ("12,500", 12),
        ("12.9", 12),
        ("abc", 0),
        ("", 0),
    ]


def test_cast_sum_is_a_number_never_in_the_data():
    assert cast_sum(create_company_db()) == 12024


def test_cast_to_real_keeps_the_decimal():
    assert cast_real_value(create_company_db(), "12.9") == pytest.approx(12.9)


# --- Problem 5: a cast on a column kills the index ---
def test_plain_salary_lookup_uses_the_index():
    assert plain_salary_uses_index(create_company_db()) is True


def test_cast_salary_lookup_scans():
    assert cast_salary_uses_index(create_company_db()) is False


def test_integer_division_truncates():
    assert int_division_average(create_company_db()) == 11571


def test_real_average_keeps_the_cents():
    assert real_average(create_company_db()) == pytest.approx(11571.42857142857)
