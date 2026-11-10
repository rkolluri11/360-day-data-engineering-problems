"""Day 35 tests: SQL window functions I (ROW_NUMBER, RANK, DENSE_RANK,
top-N per group, first/last per group, ranked leaderboard)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_row_number import rank_in_department, top_earner_per_department
from problem_02_rank_vs_dense_rank import (
    dense_rank_company,
    rank_company,
    rank_in_department as rank_in_dept,
)
from problem_03_top_n_per_group import (
    top_n_per_department,
    top_n_per_department_via_rank,
)
from problem_04_first_last_per_group import (
    first_order_per_employee,
    latest_order_per_employee,
)
from problem_05_ranked_leaderboard import (
    department_salary_leaderboard,
    employee_leaderboard,
    highest_order_per_employee,
)
from seed import create_company_db


# --- Problem 1: ROW_NUMBER ---
def test_rank_in_department_engineering():
    rows = [r for r in rank_in_department(create_company_db())
            if r[0] == "Engineering"]
    assert rows == [
        ("Engineering", "Grace Liu", 190000, 1),
        ("Engineering", "Alice Chen", 145000, 2),
        ("Engineering", "Carol Davis", 112000, 3),
        ("Engineering", "Bob Martinez", 110000, 4),
        ("Engineering", "Henry Wong", 110000, 5),
    ]


def test_row_number_never_ties():
    # 13 employees, ranks 1..5 per department, no shared rank.
    rows = rank_in_department(create_company_db())
    assert len(rows) == 13
    for dept in ("Data", "Engineering", "HR", "Legal", "Sales"):
        ranks = [r[3] for r in rows if r[0] == dept]
        assert ranks == list(range(1, len(ranks) + 1))


def test_top_earner_per_department():
    assert top_earner_per_department(create_company_db()) == [
        ("Engineering", "Grace Liu", 190000),
        ("Sales", "Irene Novak", 175000),
        ("Data", "Karen White", 160000),
        ("Legal", "Nina Patel", 125000),
        ("HR", "Mia Brown", 105000),
    ]


# --- Problem 2: RANK vs DENSE_RANK ---
def test_rank_company_tie_and_gap():
    rows = rank_company(create_company_db())
    by_name = {r[0]: r[2] for r in rows}
    assert by_name["Bob Martinez"] == 8
    assert by_name["Henry Wong"] == 8
    # The gap: after a two-way tie at 8, the next rank is 10, not 9.
    assert by_name["Mia Brown"] == 10
    assert by_name["Leo Garcia"] == 13


def test_dense_rank_company_no_gap():
    rows = dense_rank_company(create_company_db())
    by_name = {r[0]: r[2] for r in rows}
    assert by_name["Bob Martinez"] == 8
    assert by_name["Henry Wong"] == 8
    assert by_name["Mia Brown"] == 9
    assert by_name["Leo Garcia"] == 12


def test_rank_and_dense_differ_by_exactly_the_gap():
    rank = {r[0]: r[2] for r in rank_company(create_company_db())}
    dense = {r[0]: r[2] for r in dense_rank_company(create_company_db())}
    assert rank["Mia Brown"] - dense["Mia Brown"] == 1
    assert rank["Grace Liu"] == dense["Grace Liu"] == 1


def test_rank_in_department_tie_has_no_fifth():
    rows = [r for r in rank_in_dept(create_company_db())
            if r[0] == "Engineering"]
    assert [r[3] for r in rows] == [1, 2, 3, 4, 4]


# --- Problem 3: Top-N per group ---
def test_top_n_per_department_default():
    assert top_n_per_department(create_company_db()) == [
        ("Data", "Karen White", 160000, 1),
        ("Data", "Jack Thompson", 120000, 2),
        ("Engineering", "Grace Liu", 190000, 1),
        ("Engineering", "Alice Chen", 145000, 2),
        ("HR", "Mia Brown", 105000, 1),
        ("HR", "Leo Garcia", 75000, 2),
        ("Legal", "Nina Patel", 125000, 1),
        ("Sales", "Irene Novak", 175000, 1),
        ("Sales", "Frank Lopez", 98000, 2),
    ]


def test_top_n_group_smaller_than_n_sends_fewer():
    # Legal has 1 employee: top 2 per department is 9 people, not 10.
    assert len(top_n_per_department(create_company_db())) == 9
    assert len(top_n_per_department(create_company_db(), 1)) == 5


def test_top_n_via_rank_matches_here():
    # No tie sits at rank 2 in any department, so RANK <= 2 == rn <= 2.
    rn = {(r[0], r[1]) for r in top_n_per_department(create_company_db())}
    rk = {(r[0], r[1]) for r in top_n_per_department_via_rank(create_company_db())}
    assert rn == rk


# --- Problem 4: First and last per group ---
def test_first_order_per_employee():
    assert first_order_per_employee(create_company_db()) == [
        ("David Kim", 1, 12000, "2026-01-05"),
        ("Frank Lopez", 3, 15000, "2026-01-20"),
        ("Irene Novak", 5, 25000, "2026-02-10"),
    ]


def test_latest_order_per_employee():
    assert latest_order_per_employee(create_company_db()) == [
        ("David Kim", 7, None, "2026-02-20"),
        ("Frank Lopez", 8, 9000, "2026-03-01"),
        ("Irene Novak", 6, 7000, "2026-02-15"),
    ]


def test_latest_order_keeps_the_null_quote():
    # David's latest order is the pending quote: NULL amount, not zero.
    latest = {r[0]: r for r in latest_order_per_employee(create_company_db())}
    assert latest["David Kim"][2] is None
    assert latest["David Kim"][1] == 7


# --- Problem 5: Ranked leaderboard ---
def test_department_salary_leaderboard():
    assert department_salary_leaderboard(create_company_db()) == [
        ("Engineering", 667000, 1),
        ("Sales", 368000, 2),
        ("Data", 280000, 3),
        ("HR", 180000, 4),
        ("Legal", 125000, 5),
    ]


def test_employee_leaderboard_tie_in_all_three_columns():
    rows = employee_leaderboard(create_company_db())
    assert len(rows) == 13
    by_name = {r[1]: r for r in rows}
    assert by_name["Bob Martinez"] == (
        "Engineering", "Bob Martinez", 110000, 4, 8, 8)
    assert by_name["Henry Wong"] == (
        "Engineering", "Henry Wong", 110000, 4, 8, 8)
    # Mia: company RANK 10, DENSE_RANK 9 — the gap, side by side.
    assert by_name["Mia Brown"][4] == 10
    assert by_name["Mia Brown"][5] == 9


def test_highest_order_per_employee():
    assert highest_order_per_employee(create_company_db()) == [
        ("David Kim", 1, 12000),
        ("Frank Lopez", 3, 15000),
        ("Irene Novak", 5, 25000),
    ]


def test_highest_order_never_picks_the_null():
    assert all(r[2] is not None
               for r in highest_order_per_employee(create_company_db()))
