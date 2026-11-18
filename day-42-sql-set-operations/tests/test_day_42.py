"""Day 42 tests: SQL set operations — UNION vs UNION ALL, INTERSECT, EXCEPT.

Same company database as Days 35–41, plus newsletter/webinar/
unsubscribed lists and online/store orders. All expected numbers
were computed against the seed and checked by hand: departments
UNION 6, UNION ALL of DISTINCT lists 10 rows, without DISTINCT
18 rows (Engineering 6 mentions); emails UNION 7 people, UNION
ALL 10 rows, INTERSECT 3, newsletter-only alice/bob, webinar-only
frank/henry; online 4 rows $57,000, store 4 rows $29,000, UNION ALL
stack 8 rows $86,000, UNION stack 7 rows $81,000 (a real $5,000
sale lost); Engineering INTERSECT Apollo Alice/Bob/Carol,
Engineering EXCEPT Apollo Grace/Henry, Apollo INTERSECT Beacon
Alice only; departments without a budget row Legal, without
employees Operations; launch audience 5 (alice, bob, carol,
frank, henry), true reach 7 vs naive count 10.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_union_vs_union_all import (
    department_names,
    employee_departments,
    engineering_mentions_without_distinct,
    union_all_departments,
    union_all_email_count,
    union_all_without_distinct_count,
    union_departments,
    union_emails,
    union_mismatched_columns,
)
from problem_02_union_all_stacking import (
    duplicated_stacked_rows,
    lost_revenue,
    online_total,
    stacked_rows_by_date,
    stacked_union,
    stacked_union_all,
    store_total,
)
from problem_03_intersect_overlap import (
    apollo_and_beacon,
    apollo_and_beacon_union_all_count,
    apollo_or_beacon,
    engineering_on_apollo,
    newsletter_and_webinar,
)
from problem_04_except_gaps import (
    departments_without_budget_row,
    departments_without_employees,
    engineering_not_on_apollo,
    newsletter_only,
    webinar_only,
)
from problem_05_launch_audience import (
    audience_via_union_all,
    launch_audience,
    naive_contact_count,
    opted_out_overlap,
    true_reach,
)
from seed import create_company_db


@pytest.fixture
def conn():
    connection = create_company_db()
    yield connection
    connection.close()


# Problem 1 — UNION vs UNION ALL

def test_employee_departments(conn):
    assert employee_departments(conn) == ["Data", "Engineering", "HR", "Legal", "Sales"]


def test_department_names(conn):
    assert department_names(conn) == ["Data", "Engineering", "HR", "Operations", "Sales"]


def test_union_departments(conn):
    assert union_departments(conn) == [
        "Data", "Engineering", "HR", "Legal", "Operations", "Sales",
    ]


def test_union_all_departments(conn):
    rows = union_all_departments(conn)
    assert len(rows) == 10
    assert sorted(rows) == [
        "Data", "Data", "Engineering", "Engineering", "HR",
        "HR", "Legal", "Operations", "Sales", "Sales",
    ]


def test_union_all_without_distinct(conn):
    assert union_all_without_distinct_count(conn) == 18


def test_engineering_mentions_without_distinct(conn):
    assert engineering_mentions_without_distinct(conn) == 6


def test_union_emails(conn):
    assert union_emails(conn) == [
        "alice@acme.example", "bob@acme.example", "carol@acme.example",
        "david@acme.example", "frank@acme.example", "grace@acme.example",
        "henry@acme.example",
    ]


def test_union_all_email_count(conn):
    assert union_all_email_count(conn) == 10


def test_union_mismatched_columns(conn):
    import sqlite3

    with pytest.raises(sqlite3.OperationalError, match="same number of result columns"):
        union_mismatched_columns(conn)


# Problem 2 — UNION ALL stacking

def test_channel_totals(conn):
    assert online_total(conn) == (4, 57000)
    assert store_total(conn) == (4, 29000)


def test_stacked_union_all_keeps_every_sale(conn):
    assert stacked_union_all(conn) == (8, 86000)


def test_stacked_union_loses_a_real_sale(conn):
    assert stacked_union(conn) == (7, 81000)
    assert lost_revenue(conn) == 5000


def test_duplicated_stacked_row_is_a_real_second_purchase(conn):
    assert duplicated_stacked_rows(conn) == [("Frank Lopez", 5000, "2026-02-02", 2)]


def test_stacked_rows_by_date(conn):
    rows = stacked_rows_by_date(conn)
    assert len(rows) == 8
    assert rows[0] == ("David Kim", 12000, "2026-01-05")
    assert rows[-1] == ("Frank Lopez", 9000, "2026-03-01")
    assert sum(1 for r in rows if r == ("Frank Lopez", 5000, "2026-02-02")) == 2


# Problem 3 — INTERSECT

def test_engineering_on_apollo(conn):
    assert engineering_on_apollo(conn) == ["Alice Chen", "Bob Martinez", "Carol Davis"]


def test_apollo_and_beacon(conn):
    assert apollo_and_beacon(conn) == ["Alice Chen"]


def test_apollo_or_beacon(conn):
    assert apollo_or_beacon(conn) == [
        "Alice Chen", "Bob Martinez", "Carol Davis", "David Kim", "Grace Liu",
    ]


def test_apollo_beacon_union_all_counts_alice_twice(conn):
    assert apollo_and_beacon_union_all_count(conn) == 6


def test_newsletter_and_webinar(conn):
    assert newsletter_and_webinar(conn) == [
        "carol@acme.example", "david@acme.example", "grace@acme.example",
    ]


# Problem 4 — EXCEPT

def test_engineering_not_on_apollo(conn):
    assert engineering_not_on_apollo(conn) == ["Grace Liu", "Henry Wong"]


def test_newsletter_only_and_webinar_only_differ(conn):
    assert newsletter_only(conn) == ["alice@acme.example", "bob@acme.example"]
    assert webinar_only(conn) == ["frank@acme.example", "henry@acme.example"]


def test_departments_without_budget_row(conn):
    assert departments_without_budget_row(conn) == ["Legal"]


def test_departments_without_employees(conn):
    assert departments_without_employees(conn) == ["Operations"]


# Problem 5 — combined launch audience

def test_launch_audience(conn):
    assert launch_audience(conn) == [
        "alice@acme.example", "bob@acme.example", "carol@acme.example",
        "frank@acme.example", "henry@acme.example",
    ]


def test_naive_count_overstates_reach(conn):
    assert naive_contact_count(conn) == 10
    assert true_reach(conn) == 7


def test_audience_via_union_all_matches(conn):
    assert audience_via_union_all(conn) == launch_audience(conn)


def test_opted_out_overlap(conn):
    assert opted_out_overlap(conn) == ["david@acme.example", "grace@acme.example"]
