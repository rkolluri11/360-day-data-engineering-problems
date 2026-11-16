"""Day 41 tests: SQL string and date functions for messy source data.

Same company database as Days 35–40, plus staged_raw — the same
8 orders loaded dirty. All expected numbers were computed against
the seed and checked by hand: distinct customers 7 raw, 6 trimmed,
3 upper-trimmed; LENGTH('  David Kim ') 12, TRIM 9; customers
David Kim 3, Frank Lopez 3, Irene Novak 2; 7 raw region spellings,
East 4 orders $54,000, West 4 orders $27,000; CAST('12,000') 12,
CAST('$25,000') 0, naive SUM 15,041, cleaned SUM $81,000;
COUNT/AVG without NULLIF 8 and 10,125, with NULLIF 7 and
11,571.43; DATE() parses 3 of 8; months Jan (3, $35,000),
Feb (4, $37,000), Mar (1, $9,000); date span 55 days.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_trim_spaces import (
    distinct_customers_raw,
    distinct_customers_trimmed,
    distinct_customers_upper_trimmed,
    name_lengths,
    trimmed_names,
)
from problem_02_normalize_identity import (
    customer_order_counts,
    distinct_regions_raw,
    region_order_counts,
    region_totals,
)
from problem_03_replace_then_cast import (
    cast_examples,
    cleaned_amounts,
    cleaned_total,
    naive_total,
)
from problem_04_nullif_sentinel import (
    cast_na_sentinel,
    cleaned_amount_of_order,
    count_avg_no_nullif,
    count_avg_with_nullif,
)
from problem_05_normalize_dates import (
    cleaned_dates,
    date_span_days,
    directly_parseable,
    monthly_totals,
)
from seed import create_company_db


@pytest.fixture
def conn():
    connection = create_company_db()
    yield connection
    connection.close()


def test_seed_has_eight_dirty_rows(conn):
    count = conn.execute("SELECT COUNT(*) FROM staged_raw").fetchone()[0]
    assert count == 8
    row = conn.execute(
        "SELECT customer_raw, amount_text, date_text, region_raw "
        "FROM staged_raw WHERE order_id = 5"
    ).fetchone()
    assert row == ("Irene Novak", "$25,000", "02/10/2026", "EAST")


def test_distinct_customers_collapse_with_cleaning(conn):
    assert distinct_customers_raw(conn) == 7
    assert distinct_customers_trimmed(conn) == 6
    assert distinct_customers_upper_trimmed(conn) == 3


def test_trim_removes_spaces_not_letters(conn):
    assert name_lengths(conn, 1) == (12, 9)
    assert trimmed_names(conn)[0] == "David Kim"
    assert trimmed_names(conn)[3] == "FRANK LOPEZ"


def test_normalized_customer_counts(conn):
    assert customer_order_counts(conn) == {
        "David Kim": 3,
        "Frank Lopez": 3,
        "Irene Novak": 2,
    }


def test_regions_collapse_to_east_west(conn):
    assert distinct_regions_raw(conn) == 7
    assert region_order_counts(conn) == {"East": 4, "West": 4}
    assert region_totals(conn) == {"East": 54000, "West": 27000}


def test_cast_stops_at_first_bad_character(conn):
    assert cast_examples(conn) == (12, 0)
    assert naive_total(conn) == 15041


def test_replace_then_cast_recovers_real_total(conn):
    assert cleaned_amounts(conn) == [
        "12000",
        "8000",
        "15000",
        "5000",
        "25000",
        "7000",
        "N/A",
        "9000",
    ]
    assert cleaned_total(conn) == 81000


def test_na_sentinel_casts_to_zero(conn):
    assert cast_na_sentinel(conn) == 0


def test_nullif_changes_count_and_avg(conn):
    count, avg = count_avg_no_nullif(conn)
    assert count == 8
    assert avg == pytest.approx(10125.0)
    count, avg = count_avg_with_nullif(conn)
    assert count == 7
    assert avg == pytest.approx(11571.43, abs=0.01)


def test_nullif_turns_na_into_real_null(conn):
    assert cleaned_amount_of_order(conn, 7) is None
    assert cleaned_amount_of_order(conn, 5) == 25000


def test_date_parses_only_iso_directly(conn):
    assert directly_parseable(conn) == 3


def test_all_dates_normalize_to_clean_order_dates(conn):
    assert cleaned_dates(conn) == [
        "2026-01-05",
        "2026-01-12",
        "2026-01-20",
        "2026-02-02",
        "2026-02-10",
        "2026-02-15",
        "2026-02-20",
        "2026-03-01",
    ]


def test_monthly_totals_after_normalization(conn):
    assert monthly_totals(conn) == {
        "2026-01": (3, 35000),
        "2026-02": (4, 37000),
        "2026-03": (1, 9000),
    }


def test_date_span_is_55_days(conn):
    assert date_span_days(conn) == pytest.approx(55.0)
