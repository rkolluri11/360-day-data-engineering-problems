"""Day 46 tests: SQL deduplication — ROW_NUMBER vs GROUP BY vs DISTINCT.

Same company database as Days 35-45, plus a crm_contacts table
holding a messy CRM import (8 rows, 4 emails). All expected
numbers were computed against the seed and checked by hand:
3 distinct sellers, 6 (seller, region) pairs, 8 distinct full
order rows, COUNT(DISTINCT amount) 7 (NULL not counted) vs
SELECT DISTINCT amount 8 rows including NULL; UNION ALL over
online + store orders 8 rows / $86,000, UNION 7 rows / $81,000,
Frank's $5,000 on 2026-02-02 appearing twice; CRM ROW_NUMBER
keeps ids 1, 3, 5, 8 and deletes 2, 4, 6, 7; dup groups David 3,
Frank 2, Irene 2; staged_raw normalized David 3, Frank 3,
Irene 2 — 3 distinct customers.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_distinct_vs_group_by import (
    distinct_amount_count,
    distinct_amount_rows,
    distinct_full_rows,
    distinct_seller_count,
    distinct_seller_region_pairs,
    distinct_sellers,
    order_count,
    sellers_via_group_by,
)
from problem_02_identical_not_duplicate import (
    combined_all,
    combined_all_total,
    combined_distinct,
    combined_distinct_total,
    frank_feb2_rows,
    lost_by_union,
)
from problem_03_row_number_keep_one import (
    duplicate_rows,
    keep_first_per_email,
    keep_latest_per_email,
    max_copies_per_email,
    ranked_contacts,
)
from problem_04_find_duplicates_first import (
    distinct_email_count,
    duplicate_emails,
    normalized_customers,
    normalized_distinct_count,
    raw_distinct_customers,
    total_contacts,
)
from problem_05_delete_safely import (
    count_after_delete,
    delete_duplicates_keep_earliest,
    delete_in_transaction,
    rows_to_delete,
    survivors_after_delete,
)
from seed import create_company_db


@pytest.fixture
def conn():
    return create_company_db()


def test_distinct_and_group_by_agree_on_three_sellers(conn):
    assert distinct_sellers(conn) == [
        "David Kim",
        "Frank Lopez",
        "Irene Novak",
    ]
    assert sellers_via_group_by(conn) == distinct_sellers(conn)
    assert order_count(conn) == 8
    assert distinct_seller_count(conn) == 3


def test_distinct_pairs_and_full_rows(conn):
    assert distinct_seller_region_pairs(conn) == 6
    assert distinct_full_rows(conn) == 8


def test_count_distinct_ignores_null_but_select_distinct_keeps_it(conn):
    assert distinct_amount_count(conn) == 7
    assert distinct_amount_rows(conn) == [
        None,
        5000,
        7000,
        8000,
        9000,
        12000,
        15000,
        25000,
    ]


def test_union_all_keeps_both_frank_purchases(conn):
    assert combined_all_total(conn) == (8, 86000)
    assert len(combined_all(conn)) == 8
    assert frank_feb2_rows(conn) == 2


def test_union_loses_five_thousand(conn):
    assert combined_distinct_total(conn) == (7, 81000)
    assert len(combined_distinct(conn)) == 7
    assert lost_by_union(conn) == 5000


def test_row_number_ranks_each_persons_copies(conn):
    assert ranked_contacts(conn) == [
        (1, "David Kim", "david@acme.example", 1),
        (2, "David Kim", "david@acme.example", 2),
        (3, "Frank Lopez", "frank@acme.example", 1),
        (4, "Frank Lopez", "frank@acme.example", 2),
        (5, "Irene Novak", "irene@acme.example", 1),
        (6, "Irene Novak", "irene@acme.example", 2),
        (7, "David Kim", "david@acme.example", 3),
        (8, "Grace Liu", "grace@acme.example", 1),
    ]
    assert max_copies_per_email(conn) == 3


def test_keep_first_per_email(conn):
    assert keep_first_per_email(conn) == [
        (1, "David Kim", "david@acme.example"),
        (3, "Frank Lopez", "frank@acme.example"),
        (5, "Irene Novak", "irene@acme.example"),
        (8, "Grace Liu", "grace@acme.example"),
    ]
    assert duplicate_rows(conn) == [
        (2, "David Kim", "david@acme.example"),
        (4, "Frank Lopez", "frank@acme.example"),
        (6, "Irene Novak", "irene@acme.example"),
        (7, "David Kim", "david@acme.example"),
    ]


def test_keep_latest_is_a_different_decision(conn):
    assert keep_latest_per_email(conn) == [
        (4, "Frank Lopez", "frank@acme.example"),
        (6, "Irene Novak", "irene@acme.example"),
        (7, "David Kim", "david@acme.example"),
        (8, "Grace Liu", "grace@acme.example"),
    ]


def test_find_duplicates_before_deleting(conn):
    assert duplicate_emails(conn) == [
        ("david@acme.example", 3),
        ("frank@acme.example", 2),
        ("irene@acme.example", 2),
    ]
    assert total_contacts(conn) == 8
    assert distinct_email_count(conn) == 4


def test_dirty_spelling_hides_people_until_normalized(conn):
    assert len(raw_distinct_customers(conn)) == 7
    assert normalized_customers(conn) == [
        ("david kim", 3),
        ("frank lopez", 3),
        ("irene novak", 2),
    ]
    assert normalized_distinct_count(conn) == 3


def test_select_first_lists_exactly_what_delete_removes(conn):
    assert rows_to_delete(conn) == [2, 4, 6, 7]


def test_delete_keeps_earliest_and_leaves_four(conn):
    assert delete_duplicates_keep_earliest(conn) == 4
    assert count_after_delete(conn) == 4
    assert survivors_after_delete(conn) == [
        (1, "David Kim", "david@acme.example"),
        (3, "Frank Lopez", "frank@acme.example"),
        (5, "Irene Novak", "irene@acme.example"),
        (8, "Grace Liu", "grace@acme.example"),
    ]


def test_delete_in_transaction(conn):
    assert delete_in_transaction(conn) == (4, 4)
