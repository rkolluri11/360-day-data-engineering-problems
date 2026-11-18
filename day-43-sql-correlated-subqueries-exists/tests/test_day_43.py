"""Day 43 tests: SQL correlated subqueries and EXISTS — the semi-join.

Same company database as Days 35–42. All expected numbers were
computed against the seed and checked by hand: JOIN employees to
orders is 8 rows for 3 sellers (David 3, Frank 3, Irene 2);
EXISTS returns the 3 names once each. Department averages:
Engineering $133,400, Sales $122,666.67, Data $140,000, HR
$90,000, Legal $125,000 (Nina alone); above their own average:
Grace, Alice, Irene, Karen, Mia — 5. The manager list contains
a NULL (5 top-level staff), so NOT IN returns 0 rows while NOT
EXISTS returns the correct 9 non-managers; IN still finds the
4 managers. Departments with a >$150,000 earner: Data,
Engineering, Sales — 3. Above average AND has an order: Irene
Novak only. Apollo but not Beacon: Bob, Carol.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_exists_semi_join import (
    employees_without_orders,
    orders_per_seller,
    sellers_via_exists,
    sellers_via_join_distinct,
    sellers_via_join_row_count,
)
from problem_02_correlated_above_average import (
    above_company_average,
    above_department_average,
    company_average,
    department_averages,
    legal_average_is_nina,
)
from problem_03_not_in_null_trap import (
    managers_via_in,
    non_managers_via_not_exists,
    non_managers_via_not_in,
    non_managers_via_not_in_filtered,
    null_manager_count,
)
from problem_04_exists_threshold import (
    department_top_salary,
    departments_with_high_earner,
    departments_without_high_earner,
    high_earners,
)
from problem_05_combined_above_avg_seller import (
    above_average_non_sellers,
    above_average_sellers,
    apollo_not_beacon,
    sellers_below_average,
)
from seed import create_company_db


@pytest.fixture
def conn():
    connection = create_company_db()
    yield connection
    connection.close()


# Problem 1 — EXISTS, the semi-join

def test_join_counts_rows_not_people(conn):
    assert sellers_via_join_row_count(conn) == 8


def test_orders_per_seller(conn):
    assert orders_per_seller(conn) == [
        ("David Kim", 3),
        ("Frank Lopez", 3),
        ("Irene Novak", 2),
    ]


def test_sellers_via_exists(conn):
    assert sellers_via_exists(conn) == ["David Kim", "Frank Lopez", "Irene Novak"]


def test_sellers_via_join_distinct_agrees(conn):
    assert sellers_via_join_distinct(conn) == sellers_via_exists(conn)


def test_employees_without_orders(conn):
    assert employees_without_orders(conn) == [
        "Alice Chen", "Bob Martinez", "Carol Davis", "Grace Liu",
        "Henry Wong", "Jack Thompson", "Karen White", "Leo Garcia",
        "Mia Brown", "Nina Patel",
    ]


# Problem 2 — correlated subquery, above department average

def test_department_averages(conn):
    avgs = department_averages(conn)
    assert [a[0] for a in avgs] == ["Data", "Engineering", "HR", "Legal", "Sales"]
    assert avgs[0][1] == pytest.approx(140000.0)
    assert avgs[1][1] == pytest.approx(133400.0)
    assert avgs[2][1] == pytest.approx(90000.0)
    assert avgs[3][1] == pytest.approx(125000.0)
    assert avgs[4][1] == pytest.approx(122666.67, abs=0.01)
    assert [a[2] for a in avgs] == [2, 5, 2, 1, 3]


def test_above_department_average(conn):
    assert above_department_average(conn) == [
        ("Karen White", "Data", 160000),
        ("Alice Chen", "Engineering", 145000),
        ("Grace Liu", "Engineering", 190000),
        ("Mia Brown", "HR", 105000),
        ("Irene Novak", "Sales", 175000),
    ]


def test_company_average_is_not_the_comparison(conn):
    assert company_average(conn) == pytest.approx(124615.38, abs=0.01)
    assert above_company_average(conn) == [
        "Alice Chen", "Grace Liu", "Irene Novak", "Karen White", "Nina Patel",
    ]
    # Nina clears the company average but is exactly her own average;
    # Mia beats HR's average but misses the company one.
    assert "Mia Brown" not in above_company_average(conn)
    assert "Mia Brown" in [r[0] for r in above_department_average(conn)]


def test_legal_average_is_nina(conn):
    assert legal_average_is_nina(conn) == (125000.0, 1)


# Problem 3 — NOT IN vs NOT EXISTS, the NULL trap

def test_managers_via_in(conn):
    assert managers_via_in(conn) == ["Grace Liu", "Irene Novak", "Karen White", "Mia Brown"]


def test_null_manager_count(conn):
    assert null_manager_count(conn) == 5


def test_not_in_returns_nobody(conn):
    assert non_managers_via_not_in(conn) == []


def test_not_exists_returns_nine(conn):
    assert non_managers_via_not_exists(conn) == [
        "Alice Chen", "Bob Martinez", "Carol Davis", "David Kim",
        "Frank Lopez", "Henry Wong", "Jack Thompson", "Leo Garcia",
        "Nina Patel",
    ]


def test_not_in_filtered_recovers(conn):
    assert non_managers_via_not_in_filtered(conn) == non_managers_via_not_exists(conn)


# Problem 4 — EXISTS with a threshold

def test_departments_with_high_earner(conn):
    assert departments_with_high_earner(conn) == ["Data", "Engineering", "Sales"]


def test_departments_without_high_earner(conn):
    # Operations qualifies too: it has a budget row but no employees at all.
    # Legal never appears — it has people but no departments-table row (Day 42).
    assert departments_without_high_earner(conn) == ["HR", "Operations"]


def test_high_earners(conn):
    assert high_earners(conn) == [
        ("Karen White", "Data", 160000),
        ("Grace Liu", "Engineering", 190000),
        ("Irene Novak", "Sales", 175000),
    ]


def test_department_top_salary(conn):
    assert department_top_salary(conn) == [
        ("Data", 160000),
        ("Engineering", 190000),
        ("HR", 105000),
        ("Legal", 125000),
        ("Sales", 175000),
    ]


# Problem 5 — combined

def test_above_average_sellers(conn):
    assert above_average_sellers(conn) == ["Irene Novak"]


def test_above_average_non_sellers(conn):
    assert above_average_non_sellers(conn) == [
        "Alice Chen", "Grace Liu", "Karen White", "Mia Brown",
    ]


def test_apollo_not_beacon(conn):
    assert apollo_not_beacon(conn) == ["Bob Martinez", "Carol Davis"]


def test_sellers_below_average(conn):
    assert sellers_below_average(conn) == ["David Kim", "Frank Lopez"]
