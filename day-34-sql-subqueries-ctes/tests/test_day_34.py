"""Day 34 tests: SQL subqueries and CTEs (scalar/IN, EXISTS, CTE basics,
chained CTEs, recursive CTE)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_scalar_and_in_subqueries import (
    above_company_average,
    above_department_average,
    in_big_budget_departments,
)
from problem_02_exists_correlated import (
    departments_with_high_earner,
    non_managers_via_not_exists,
    non_managers_via_not_in,
    on_active_project,
    with_no_assignment,
)
from problem_03_cte_basics import (
    above_average_orders_via_cte,
    above_department_average_via_cte,
    departments_above_avg_budget_via_cte,
)
from problem_04_chained_ctes import (
    above_average_projects,
    above_average_regions,
    project_hours_by_project,
)
from problem_05_recursive_cte import (
    manager_chain,
    max_org_depth,
    org_depths,
    team_rollup,
)
from seed import create_company_db


# --- Problem 1: scalar and IN subqueries ---
def test_above_department_average():
    assert above_department_average(create_company_db()) == [
        "Alice Chen",
        "Grace Liu",
        "Irene Novak",
        "Karen White",
        "Mia Brown",
    ]


def test_above_department_average_excludes_at_average():
    # Nina Patel earns exactly Legal's average (125,000, sole member).
    assert "Nina Patel" not in above_department_average(create_company_db())


def test_above_company_average():
    assert above_company_average(create_company_db()) == [
        "Alice Chen",
        "Grace Liu",
        "Irene Novak",
        "Karen White",
        "Nina Patel",
    ]


def test_department_vs_company_average_differ_by_one():
    # Same shape, different denominator: Mia swaps for Nina.
    dept = set(above_department_average(create_company_db()))
    company = set(above_company_average(create_company_db()))
    assert dept - company == {"Mia Brown"}
    assert company - dept == {"Nina Patel"}


def test_in_big_budget_departments():
    assert in_big_budget_departments(create_company_db()) == [
        "Alice Chen",
        "Bob Martinez",
        "Carol Davis",
        "David Kim",
        "Frank Lopez",
        "Grace Liu",
        "Henry Wong",
        "Irene Novak",
    ]


def test_in_big_budget_departments_threshold():
    # Only Engineering clears 5,000,000.
    assert in_big_budget_departments(create_company_db(), 5000000) == [
        "Alice Chen",
        "Bob Martinez",
        "Carol Davis",
        "Grace Liu",
        "Henry Wong",
    ]


# --- Problem 2: EXISTS and the NOT IN NULL trap ---
def test_on_active_project():
    assert on_active_project(create_company_db()) == [
        "Alice Chen",
        "Bob Martinez",
        "Carol Davis",
        "David Kim",
        "Grace Liu",
    ]


def test_on_active_project_excludes_completed_only():
    # Jack's only assignment is Cypress (completed).
    assert "Jack Thompson" not in on_active_project(create_company_db())


def test_with_no_assignment():
    assert with_no_assignment(create_company_db()) == [
        "Frank Lopez",
        "Henry Wong",
        "Irene Novak",
        "Karen White",
        "Leo Garcia",
        "Mia Brown",
        "Nina Patel",
    ]


def test_departments_with_high_earner():
    assert departments_with_high_earner(create_company_db()) == [
        "Data",
        "Engineering",
        "Sales",
    ]


def test_not_in_null_trap_returns_nothing():
    # manager_id contains NULLs -> NOT IN is UNKNOWN for everyone.
    assert non_managers_via_not_in(create_company_db()) == []


def test_not_exists_gives_correct_non_managers():
    assert non_managers_via_not_exists(create_company_db()) == [
        "Alice Chen",
        "Bob Martinez",
        "Carol Davis",
        "David Kim",
        "Frank Lopez",
        "Henry Wong",
        "Jack Thompson",
        "Leo Garcia",
        "Nina Patel",
    ]


# --- Problem 3: CTE basics ---
def test_cte_matches_subquery_for_above_department_average():
    # The CTE rewrite must agree with the correlated subquery exactly.
    assert above_department_average_via_cte(
        create_company_db()
    ) == above_department_average(create_company_db())


def test_departments_above_avg_budget():
    assert departments_above_avg_budget_via_cte(create_company_db()) == [
        ("Engineering", 5000000),
        ("Sales", 3000000),
    ]


def test_above_average_orders_via_cte():
    # Avg order amount is 81,000 / 7 = ~11,571; NULL order excluded.
    assert above_average_orders_via_cte(create_company_db()) == [
        (1, "East", 12000),
        (3, "West", 15000),
        (5, "East", 25000),
    ]


# --- Problem 4: chained CTEs ---
def test_project_hours_by_project():
    assert project_hours_by_project(create_company_db()) == [
        ("Apollo", 35),
        ("Beacon", 33),
        ("Cypress", 28),
    ]


def test_project_hours_excludes_empty_project():
    names = [name for name, _ in project_hours_by_project(create_company_db())]
    assert "Delta" not in names  # Delta has no assignments


def test_above_average_projects():
    # Average of 35, 33, 28 is 32: Apollo and Beacon clear it.
    assert above_average_projects(create_company_db()) == [
        ("Apollo", 35),
        ("Beacon", 33),
    ]


def test_above_average_regions():
    # East 54,000 vs West 27,000, average 40,500: East alone.
    assert above_average_regions(create_company_db()) == [("East", 54000)]


# --- Problem 5: recursive CTE ---
def test_org_depths():
    assert org_depths(create_company_db()) == [
        ("Grace Liu", 0),
        ("Irene Novak", 0),
        ("Karen White", 0),
        ("Mia Brown", 0),
        ("Nina Patel", 0),
        ("Alice Chen", 1),
        ("Bob Martinez", 1),
        ("Carol Davis", 1),
        ("David Kim", 1),
        ("Frank Lopez", 1),
        ("Henry Wong", 1),
        ("Jack Thompson", 1),
        ("Leo Garcia", 1),
    ]


def test_max_org_depth():
    assert max_org_depth(create_company_db()) == 1


def test_team_rollup():
    assert team_rollup(create_company_db()) == [
        ("Grace Liu", 4, 477000),
        ("Irene Novak", 2, 193000),
        ("Karen White", 1, 120000),
        ("Mia Brown", 1, 75000),
    ]


def test_team_rollup_excludes_manager_with_no_team():
    names = [name for name, _, _ in team_rollup(create_company_db())]
    assert "Nina Patel" not in names


def test_manager_chain():
    assert manager_chain(create_company_db(), 2) == ["Grace Liu"]  # Alice
    assert manager_chain(create_company_db(), 11) == ["Mia Brown"]  # Leo
    assert manager_chain(create_company_db(), 1) == []  # Grace: no manager
