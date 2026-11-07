"""Day 33 tests: SQL aggregations (GROUP BY, HAVING, grain, conditional
aggregation, combined rollups)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_group_by_basics import company_totals, department_salary_summary
from problem_02_having import (
    departments_with_high_avg_salary,
    departments_with_min_headcount,
    high_earner_counts,
)
from problem_03_grain_trap import (
    assignment_grain_counts,
    naive_total_salary_via_join,
    true_total_salary_aggregate_first,
    true_total_salary_assigned,
)
from problem_04_conditional_aggregation import (
    high_earner_stats_by_department,
    order_stats_by_region,
)
from problem_05_combined_reporting import project_hours_rollup, region_revenue_above
from seed import create_company_db


# --- Problem 1: GROUP BY basics ---
def test_department_salary_summary_exact():
    rows = department_salary_summary(create_company_db())
    assert len(rows) == 5  # Operations has no employees -> no group
    assert rows[0] == ("Data", 2, 280000, 140000.0)
    assert rows[1] == ("Engineering", 5, 667000, 133400.0)
    assert rows[2] == ("HR", 2, 180000, 90000.0)
    assert rows[3] == ("Legal", 1, 125000, 125000.0)
    assert rows[4][0] == "Sales" and rows[4][1] == 3 and rows[4][2] == 368000
    assert rows[4][3] == pytest.approx(368000 / 3)


def test_department_summary_excludes_empty_department():
    departments = [row[0] for row in department_salary_summary(create_company_db())]
    assert "Operations" not in departments


def test_company_totals():
    headcount, total, avg = company_totals(create_company_db())
    assert headcount == 13
    assert total == 1620000
    assert avg == pytest.approx(1620000 / 13)


# --- Problem 2: HAVING ---
def test_high_avg_salary_departments():
    rows = departments_with_high_avg_salary(create_company_db(), 120000)
    names = [name for name, _ in rows]
    assert names == ["Data", "Engineering", "Legal", "Sales"]  # ordered by avg DESC
    assert rows[0][1] == pytest.approx(140000.0)
    assert rows[3][1] == pytest.approx(368000 / 3)


def test_min_headcount_departments():
    assert departments_with_min_headcount(create_company_db(), 3) == [
        ("Engineering", 5),
        ("Sales", 3),
    ]


def test_where_filters_rows_before_grouping():
    # HR vanishes: neither Leo (75,000) nor Mia (105,000) clears 120,000,
    # so HR produces no group at all. Jack at exactly 120,000 is excluded.
    assert high_earner_counts(create_company_db()) == [
        ("Data", 1),
        ("Engineering", 2),
        ("Legal", 1),
        ("Sales", 1),
    ]


# --- Problem 3: grain trap ---
def test_naive_join_sum_double_counts():
    assert naive_total_salary_via_join(create_company_db()) == 1029000
    assert naive_total_salary_via_join(create_company_db()) != 772000


def test_true_assigned_salary_total():
    assert true_total_salary_assigned(create_company_db()) == 772000


def test_join_grain_counts_differ():
    rows, distinct_people = assignment_grain_counts(create_company_db())
    assert rows == 8  # one row per assignment
    assert distinct_people == 6  # Alice and Carol appear twice


def test_aggregate_first_fix_matches_true_total():
    assert true_total_salary_aggregate_first(create_company_db()) == 772000
    assert (
        true_total_salary_aggregate_first(create_company_db())
        == true_total_salary_assigned(create_company_db())
    )


# --- Problem 4: conditional aggregation + NULLs ---
def test_high_earner_stats_by_department():
    assert high_earner_stats_by_department(create_company_db()) == [
        ("Data", 2, 2, 280000),
        ("Engineering", 5, 2, 335000),
        ("HR", 2, 0, 0),  # COALESCE keeps the empty SUM at 0, not NULL
        ("Legal", 1, 1, 125000),
        ("Sales", 3, 1, 175000),
    ]


def test_null_amount_skipped_by_count_and_sum():
    rows = order_stats_by_region(create_company_db())
    assert rows == [("East", 4, 4, 54000), ("West", 4, 3, 27000)]
    # West: 4 order rows, only 3 amounts — order 7's NULL is skipped.


def test_total_revenue_across_regions():
    rows = order_stats_by_region(create_company_db())
    assert sum(row[3] for row in rows) == 81000  # 54,000 + 27,000
    assert sum(row[1] for row in rows) == 8  # COUNT(*) rows
    assert sum(row[2] for row in rows) == 7  # COUNT(amount) amounts


# --- Problem 5: combined reporting ---
def test_project_hours_rollup():
    rows = project_hours_rollup(create_company_db(), 10)
    assert len(rows) == 3  # Delta (0 hours) is dropped by HAVING
    assert rows[0][0] == "Apollo" and rows[0][1] == 3 and rows[0][2] == 35
    assert rows[0][3] == pytest.approx(35 / 3)
    assert rows[1] == ("Beacon", 3, 33, pytest.approx(11.0))
    assert rows[2] == ("Cypress", 2, 28, pytest.approx(14.0))


def test_project_rollup_excludes_delta():
    names = [row[0] for row in project_hours_rollup(create_company_db(), 10)]
    assert "Delta" not in names


def test_region_revenue_above_threshold():
    assert region_revenue_above(create_company_db(), 30000) == [("East", 4, 54000)]
    assert region_revenue_above(create_company_db(), 20000) == [
        ("East", 4, 54000),
        ("West", 4, 27000),
    ]
