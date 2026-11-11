"""Day 36 tests: SQL window functions II (LAG/LEAD, change vs previous,
running totals, moving averages, ROWS vs RANGE frames)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_lag_lead import (
    next_salary_in_department,
    prev_salary_in_department,
)
from problem_02_change_vs_previous import largest_drop, order_changes
from problem_03_running_total import (
    final_totals_per_employee,
    running_total_all_orders,
    running_total_per_employee,
)
from problem_04_moving_average import (
    cumulative_average,
    moving_average_3,
    moving_average_per_employee,
)
from problem_05_name_your_frame import (
    order_window_view,
    salary_running_rows_vs_range,
)
from seed import create_company_db


# --- Problem 1: LAG / LEAD ---
def test_prev_salary_engineering():
    rows = [r for r in prev_salary_in_department(create_company_db())
            if r[0] == "Engineering"]
    assert rows == [
        ("Engineering", "Grace Liu", 190000, None, None),
        ("Engineering", "Alice Chen", 145000, 190000, -45000),
        ("Engineering", "Carol Davis", 112000, 145000, -33000),
        ("Engineering", "Bob Martinez", 110000, 112000, -2000),
        ("Engineering", "Henry Wong", 110000, 110000, 0),
    ]


def test_tie_gap_is_zero():
    rows = {r[1]: r for r in prev_salary_in_department(create_company_db())}
    assert rows["Henry Wong"][4] == 0
    assert rows["Alice Chen"][4] == -45000


def test_next_salary_last_row_is_null():
    rows = {r[1]: r for r in next_salary_in_department(create_company_db())}
    assert rows["Grace Liu"][3] == 145000
    assert rows["Henry Wong"][3] is None
    assert rows["Leo Garcia"][3] is None


# --- Problem 2: Change vs previous ---
def test_order_changes_frank():
    rows = [r for r in order_changes(create_company_db())
            if r[0] == "Frank Lopez"]
    assert rows == [
        ("Frank Lopez", "2026-01-20", 15000, None, None, None),
        ("Frank Lopez", "2026-02-02", 5000, 15000, -10000, -66.67),
        ("Frank Lopez", "2026-03-01", 9000, 5000, 4000, 80.0),
    ]


def test_first_order_change_is_null_not_zero():
    rows = order_changes(create_company_db())
    firsts = [r for r in rows if r[3] is None]
    assert len(firsts) == 3
    assert all(r[4] is None and r[5] is None for r in firsts)


def test_largest_drop_is_irene():
    assert largest_drop(create_company_db()) == (
        "Irene Novak", "2026-02-15", 7000, 25000, -18000)


def test_null_order_change_is_null():
    rows = [r for r in order_changes(create_company_db())
            if r[0] == "David Kim"]
    assert rows[2] == ("David Kim", "2026-02-20", None, 8000, None, None)


# --- Problem 3: Running total ---
def test_running_total_david_sticks_on_null():
    rows = [r for r in running_total_per_employee(create_company_db())
            if r[0] == "David Kim"]
    assert rows == [
        ("David Kim", "2026-01-05", 12000, 12000),
        ("David Kim", "2026-01-12", 8000, 20000),
        ("David Kim", "2026-02-20", None, 20000),
    ]


def test_running_total_all_orders():
    assert [r[2] for r in running_total_all_orders(create_company_db())] == [
        12000, 20000, 35000, 40000, 65000, 72000, 72000, 81000]


def test_final_totals_per_employee():
    assert final_totals_per_employee(create_company_db()) == [
        ("David Kim", 20000),
        ("Frank Lopez", 29000),
        ("Irene Novak", 32000),
    ]


# --- Problem 4: Moving average ---
def test_moving_average_3_values():
    rows = moving_average_3(create_company_db())
    by_date = {r[0]: r[2] for r in rows}
    assert by_date["2026-01-05"] == 12000.0
    assert by_date["2026-01-12"] == 10000.0
    assert by_date["2026-02-10"] == 15000.0
    assert by_date["2026-02-15"] == pytest.approx(12333.333333333334)
    assert by_date["2026-03-01"] == 8000.0


def test_moving_average_skips_null():
    # Feb 20 window holds 25,000, 7,000, NULL — averaged over two.
    by_date = {r[0]: r[2] for r in moving_average_3(create_company_db())}
    assert by_date["2026-02-20"] == 16000.0


def test_moving_average_per_employee_david():
    rows = [r for r in moving_average_per_employee(create_company_db())
            if r[0] == "David Kim"]
    assert [r[3] for r in rows] == [12000.0, 10000.0, 10000.0]


def test_cumulative_average_final():
    rows = cumulative_average(create_company_db())
    assert rows[-1][2] == pytest.approx(11571.428571428572)
    assert rows[0][2] == 12000.0


# --- Problem 5: Name your frame ---
def test_rows_vs_range_tie():
    rows = {r[0]: r for r in salary_running_rows_vs_range(create_company_db())}
    # Bob and Henry tie at $110,000: RANGE pulls Henry into Bob's total.
    assert rows["Bob Martinez"][2] == 1137000
    assert rows["Bob Martinez"][3] == 1247000
    assert rows["Henry Wong"][2] == 1247000
    assert rows["Henry Wong"][3] == 1247000


def test_rows_vs_range_agree_without_ties():
    rows = {r[0]: r for r in salary_running_rows_vs_range(create_company_db())}
    assert rows["Grace Liu"][2] == rows["Grace Liu"][3] == 190000
    assert rows["Leo Garcia"][2] == rows["Leo Garcia"][3] == 1620000


def test_order_window_view_irene():
    rows = [r for r in order_window_view(create_company_db())
            if r[0] == "Irene Novak"]
    assert rows[1] == (
        "Irene Novak", "2026-02-15", 7000, 25000, -18000, 32000, 16000.0)


def test_order_window_view_has_all_orders():
    assert len(order_window_view(create_company_db())) == 8
