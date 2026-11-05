"""Day 32 tests: SQL JOINs (INNER, LEFT, RIGHT/FULL equivalents, fanout)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_inner_join import departments_with_employees, employees_with_location
from problem_02_left_join import (
    all_employees_with_location,
    departments_without_employees,
    employees_without_assignments,
)
from problem_03_right_full_join import (
    departments_with_employees_right,
    full_employee_department,
)
from problem_04_join_fanout import (
    distinct_projects_for,
    joined_assignment_rows,
    naive_total_hours_with_tags,
    true_total_hours,
)
from problem_05_combined_join_reads import (
    assignments_with_location,
    engineering_active_leaderboard,
    unassigned_engineers,
)
from seed import create_company_db


# --- Problem 1: INNER JOIN ---
def test_inner_join_drops_unmatched_both_sides():
    rows = employees_with_location(create_company_db())
    assert len(rows) == 12  # Nina (Legal, no dept row) dropped
    assert all(name != "Nina Patel" for name, _, _ in rows)
    assert rows[0] == ("Alice Chen", "Engineering", "San Francisco")
    assert ("Grace Liu", "Engineering", "San Francisco") in rows


def test_inner_join_drops_empty_department():
    assert departments_with_employees(create_company_db()) == [
        "Data",
        "Engineering",
        "HR",
        "Sales",
    ]  # Operations (no employees) dropped


# --- Problem 2: LEFT JOIN ---
def test_left_join_keeps_all_employees_with_null():
    rows = all_employees_with_location(create_company_db())
    assert len(rows) == 13
    assert ("Nina Patel", "Legal", None) in rows


def test_left_join_finds_orphans():
    assert departments_without_employees(create_company_db()) == ["Operations"]
    assert employees_without_assignments(create_company_db()) == [
        "Frank Lopez",
        "Henry Wong",
        "Irene Novak",
        "Karen White",
        "Leo Garcia",
        "Mia Brown",
        "Nina Patel",
    ]


# --- Problem 3: RIGHT / FULL JOIN equivalents ---
def test_right_join_equivalent_keeps_empty_department():
    rows = departments_with_employees_right(create_company_db())
    assert len(rows) == 13  # 12 employee rows + 1 Operations NULL row
    assert ("Operations", None) in rows


def test_full_join_equivalent_keeps_both_orphans():
    rows = full_employee_department(create_company_db())
    assert len(rows) == 14  # 13 employee rows + 1 Operations row
    assert ("Nina Patel", None) in rows
    assert (None, "Operations") in rows


# --- Problem 4: fanout ---
def test_fanout_multiplies_rows():
    rows = joined_assignment_rows(create_company_db())
    assert len(rows) == 8  # 8 assignments, not 13 employees
    alice_rows = [r for r in rows if r[0] == "Alice Chen"]
    assert len(alice_rows) == 2  # Alice appears once per assignment


def test_distinct_undoes_fanout_for_counting():
    assert distinct_projects_for(create_company_db(), "Alice Chen") == [
        "Apollo",
        "Beacon",
    ]
    assert distinct_projects_for(create_company_db(), "Bob Martinez") == ["Apollo"]


def test_fanout_double_count_trap():
    # Apollo's 35 hours counted twice (2 tags): 70 + 33 + 28 = 131.
    assert naive_total_hours_with_tags(create_company_db()) == 131
    # True total over assignments alone: 96.
    assert true_total_hours(create_company_db()) == 96


# --- Problem 5: combined join + filter + sort ---
def test_engineering_active_leaderboard():
    assert engineering_active_leaderboard(create_company_db(), 3) == [
        ("Alice Chen", "Apollo", 20),
        ("Alice Chen", "Beacon", 15),
        ("Grace Liu", "Beacon", 12),
    ]


def test_unassigned_engineers():
    assert unassigned_engineers(create_company_db()) == ["Henry Wong"]


def test_assignments_with_location_four_tables():
    assert assignments_with_location(create_company_db(), 3) == [
        ("Alice Chen", "Apollo", "San Francisco", 20),
        ("Jack Thompson", "Cypress", "Austin", 20),
        ("Alice Chen", "Beacon", "San Francisco", 15),
    ]
