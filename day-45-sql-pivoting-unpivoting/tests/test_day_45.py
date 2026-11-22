"""Day 45 tests: SQL pivoting and unpivoting — reshaping data for reporting.

Same company database as Days 35-44, plus a monthly_sales_wide
table holding the pivoted shape. All expected numbers were
computed against the seed and checked by hand: pivot seller x
month David 20000/0/0, Frank 15000/5000/9000, Irene 0/32000/0;
month totals Jan 35000, Feb 37000, Mar 9000; grand total $81,000
over 8 orders, 7 priced; David Feb COUNT(*) 1, COUNT(amount) 0,
SUM NULL; raw pivot has 4 NULL cells of 9; region pivot David
East 20000 / West 0, Frank East 9000 / West 20000, Irene East
25000 / West 7000, region totals East 54000 / West 27000;
unpivot keeps 9 rows with NULLs, 5 priced rows totalling $81,000;
months present 01/02/03, no April; round trip 8 orders -> 5 rows.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_pivot_monthly import (
    grand_total,
    month_totals,
    pivot_monthly,
    pivot_reconciles,
    pivot_with_totals,
)
from problem_02_null_vs_zero import (
    all_orders,
    david_february,
    null_cells,
    priced_orders,
    raw_pivot,
)
from problem_03_pivot_region import (
    pivot_region,
    pivot_region_reconciles,
    region_totals,
)
from problem_04_unpivot import (
    null_rows_in_unpivot,
    unpivot_all,
    unpivot_priced,
    unpivot_priced_total,
)
from problem_05_dynamic_and_roundtrip import (
    dynamic_pivot,
    months_present,
    original_order_count,
    roundtrip_loses_rows,
    roundtrip_row_count,
    total_if_total_row_pivoted,
)
from seed import create_company_db


@pytest.fixture
def conn():
    return create_company_db()


def test_pivot_monthly_is_three_rows_nine_cells(conn):
    assert pivot_monthly(conn) == [
        ("David Kim", 20000, 0, 0),
        ("Frank Lopez", 15000, 5000, 9000),
        ("Irene Novak", 0, 32000, 0),
    ]


def test_pivot_with_totals(conn):
    assert pivot_with_totals(conn) == [
        ("David Kim", 20000, 0, 0, 20000),
        ("Frank Lopez", 15000, 5000, 9000, 29000),
        ("Irene Novak", 0, 32000, 0, 32000),
    ]


def test_month_totals_and_grand_total(conn):
    assert month_totals(conn) == [("01", 35000), ("02", 37000), ("03", 9000)]
    assert grand_total(conn) == 81000


def test_pivot_reconciles_to_long_table(conn):
    assert pivot_reconciles(conn)


def test_raw_pivot_has_nulls_not_zeros(conn):
    assert raw_pivot(conn) == [
        ("David Kim", 20000, None, None),
        ("Frank Lopez", 15000, 5000, 9000),
        ("Irene Novak", None, 32000, None),
    ]
    assert null_cells(conn) == 4


def test_david_february_is_one_order_zero_priced(conn):
    assert david_february(conn) == (1, 0, None)


def test_priced_vs_all_orders(conn):
    assert priced_orders(conn) == 7
    assert all_orders(conn) == 8


def test_pivot_region(conn):
    assert pivot_region(conn) == [
        ("David Kim", 20000, 0),
        ("Frank Lopez", 9000, 20000),
        ("Irene Novak", 25000, 7000),
    ]
    assert region_totals(conn) == [("East", 54000), ("West", 27000)]
    assert pivot_region_reconciles(conn)


def test_unpivot_all_keeps_nine_rows_with_nulls(conn):
    rows = unpivot_all(conn)
    assert len(rows) == 9
    assert null_rows_in_unpivot(conn) == 4
    assert ("David Kim", "01", 20000) in rows
    assert ("David Kim", "02", None) in rows


def test_unpivot_priced_is_five_rows(conn):
    assert unpivot_priced(conn) == [
        ("David Kim", "01", 20000),
        ("Frank Lopez", "01", 15000),
        ("Frank Lopez", "02", 5000),
        ("Frank Lopez", "03", 9000),
        ("Irene Novak", "02", 32000),
    ]
    assert unpivot_priced_total(conn) == 81000


def test_months_present_has_no_april(conn):
    assert months_present(conn) == ["01", "02", "03"]


def test_dynamic_pivot_matches_for_present_months(conn):
    assert dynamic_pivot(conn, ["01", "02", "03"]) == [
        ("David Kim", 20000, 0, 0),
        ("Frank Lopez", 15000, 5000, 9000),
        ("Irene Novak", 0, 32000, 0),
    ]


def test_dynamic_pivot_gives_zero_column_for_missing_month(conn):
    rows = dynamic_pivot(conn, ["01", "02", "03", "04"])
    assert [r[4] for r in rows] == [0, 0, 0]


def test_roundtrip_loses_rows(conn):
    assert roundtrip_row_count(conn) == 5
    assert original_order_count(conn) == 8
    assert roundtrip_loses_rows(conn)


def test_pivoting_a_total_row_double_counts(conn):
    assert total_if_total_row_pivoted(conn) == 162000
