"""Day 31 tests: SQL SELECT, WHERE, ORDER BY (SQL block start)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_explicit_columns import directory, roster
from problem_02_where_filtering import by_department_and_salary, by_name_prefix
from problem_03_order_by_top_n import lowest_earners, top_earners
from problem_04_null_distinct import (
    distinct_departments,
    distinct_titles_in_department,
    employees_with_broken_null_test,
    employees_without_manager,
    manager_counts,
)
from problem_05_combined_reads import (
    cross_department_shortlist,
    departments_with_high_earners,
    high_earner_shortlist,
)
from seed import create_company_db


# --- Problem 1: explicit columns ---
def test_roster_exact_columns_and_order():
    rows = roster(create_company_db())
    assert len(rows) == 12
    assert all(len(row) == 3 for row in rows)  # no id, no hire_date
    assert rows[0] == ("Grace Liu", "Engineering", 190000)
    assert rows[1] == ("Alice Chen", "Engineering", 145000)


def test_directory_aliases_keep_values():
    rows = directory(create_company_db())
    assert rows[0] == ("Grace Liu", "VP Engineering")
    assert len(rows) == 12


# --- Problem 2: WHERE filtering ---
def test_department_and_salary_and_logic():
    rows = by_department_and_salary(create_company_db(), "Engineering", 110000)
    # Strictly above 110k: Grace, Alice, Carol — NOT Bob/Henry at exactly 110k.
    assert rows == [
        ("Grace Liu", 190000),
        ("Alice Chen", 145000),
        ("Carol Davis", 112000),
    ]


def test_department_filter_excludes_other_departments():
    rows = by_department_and_salary(create_company_db(), "Sales", 90000)
    assert rows == [
        ("David Kim", 95000),
        ("Frank Lopez", 98000),
        ("Irene Novak", 175000),
    ]


def test_name_prefix_like_and_empty():
    assert by_name_prefix(create_company_db(), "C") == ["Carol Davis"]
    assert by_name_prefix(create_company_db(), "Z") == []


# --- Problem 3: ORDER BY + LIMIT ---
def test_top_earners_order_and_limit():
    assert top_earners(create_company_db(), 5) == [
        ("Grace Liu", 190000),
        ("Irene Novak", 175000),
        ("Karen White", 160000),
        ("Alice Chen", 145000),
        ("Jack Thompson", 120000),
    ]


def test_tie_break_by_name():
    rows = top_earners(create_company_db(), 12)
    tied = [row for row in rows if row[1] == 110000]
    assert tied == [("Bob Martinez", 110000), ("Henry Wong", 110000)]


def test_lowest_earners_asc_and_limit_beyond_rows():
    assert lowest_earners(create_company_db(), 3) == [
        ("Leo Garcia", 75000),
        ("David Kim", 95000),
        ("Frank Lopez", 98000),
    ]
    assert len(top_earners(create_company_db(), 100)) == 12


# --- Problem 4: NULL and DISTINCT ---
def test_without_manager_uses_is_null():
    assert sorted(employees_without_manager(create_company_db())) == [
        "Grace Liu",
        "Irene Novak",
        "Karen White",
        "Mia Brown",
    ]


def test_equals_null_matches_nothing():
    assert employees_with_broken_null_test(create_company_db()) == []


def test_distinct_departments_and_titles():
    assert distinct_departments(create_company_db()) == [
        "Data",
        "Engineering",
        "HR",
        "Sales",
    ]
    assert distinct_titles_in_department(create_company_db(), "Engineering") == [
        "Data Engineer",
        "Senior Data Engineer",
        "VP Engineering",
    ]


def test_manager_counts_show_null_semantics():
    # 12 rows, 8 non-NULL manager_ids, 4 distinct managers.
    assert manager_counts(create_company_db()) == (12, 8, 4)


# --- Problem 5: combined precise reads ---
def test_high_earner_shortlist_combined():
    assert high_earner_shortlist(create_company_db(), 120000, 5) == [
        ("Grace Liu", "VP Engineering", 190000),
        ("Irene Novak", "VP Sales", 175000),
        ("Karen White", "Head of Data", 160000),
        ("Alice Chen", "Senior Data Engineer", 145000),
        ("Jack Thompson", "Analytics Engineer", 120000),
    ]


def test_departments_with_high_earners():
    # HR's max is 105k, so HR drops out at a 120k threshold.
    assert departments_with_high_earners(create_company_db(), 120000) == [
        "Data",
        "Engineering",
        "Sales",
    ]


def test_cross_department_shortlist_with_in():
    assert cross_department_shortlist(
        create_company_db(), ("Engineering", "Data"), 110000, 4
    ) == [
        ("Grace Liu", "Engineering", 190000),
        ("Karen White", "Data", 160000),
        ("Alice Chen", "Engineering", 145000),
        ("Jack Thompson", "Data", 120000),
    ]
