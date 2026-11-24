"""Tests for Day 47: SCD Type 1/2/3 in pure SQL with MERGE.

Every number was verified against the seeded company database by
running the queries in place: 3 dim rows at the start, 4 after the
three changes, 5 after the MERGE batch (4 current).
"""

from __future__ import annotations

import sqlite3

import pytest

from seed import create_company_db
from problem_01_type1_overwrite import (
    apply_type1_correction,
    david_row_count,
    david_salary,
    david_valid_from,
    old_salary_survives,
)
from problem_02_type2_new_row import (
    apply_type2_move,
    frank_asof,
    frank_current,
    frank_has_overlap,
    frank_rows,
)
from problem_03_type3_previous_value import (
    apply_type3_region_change,
    irene_region_asof,
    irene_row,
    irene_row_count,
)
from problem_04_asof_query import (
    apply_all_three,
    as_of,
    current_view,
    dim_row_count,
)
from problem_05_merge_batch import (
    MERGE_SQL,
    apply_merge_batch,
    batch_totals,
    grace_row,
)


@pytest.fixture
def conn() -> sqlite3.Connection:
    return create_company_db()


def test_seed_has_three_current_dim_rows(conn):
    assert conn.execute("SELECT COUNT(*) FROM dim_employee_scd").fetchone()[0] == 3
    assert conn.execute(
        "SELECT COUNT(*) FROM dim_employee_scd WHERE is_current = 1"
    ).fetchone()[0] == 3


def test_type1_overwrites_salary_in_place(conn):
    apply_type1_correction(conn)
    assert david_salary(conn) == 96000
    assert david_row_count(conn) == 1
    assert david_valid_from(conn) == "2026-01-01"


def test_type1_old_value_is_gone(conn):
    apply_type1_correction(conn)
    assert old_salary_survives(conn) is False


def test_type2_gives_frank_two_rows(conn):
    apply_type2_move(conn)
    assert frank_rows(conn) == [
        ("Sales", 98000, "2026-01-01", "2026-03-01", 0),
        ("Data", 115000, "2026-03-01", "9999-12-31", 1),
    ]
    assert frank_current(conn) == ("Data", 115000, "2026-03-01")


def test_type2_no_overlap_and_no_gap(conn):
    apply_type2_move(conn)
    assert frank_has_overlap(conn) is False
    # Frank exists on every date around the change, exactly once.
    assert frank_asof(conn, "2026-02-28") == ("Sales", 98000)
    assert frank_asof(conn, "2026-03-01") == ("Data", 115000)


def test_type3_keeps_one_previous_region(conn):
    apply_type3_region_change(conn)
    assert irene_row(conn) == ("West", "East", 175000, "2026-01-01")
    assert irene_row_count(conn) == 1


def test_type3_asof_cannot_recover_east(conn):
    # The honest Type 3 limit: the as-of query sees West even for
    # February, because the single row was overwritten. Only
    # previous_region remembers East.
    apply_type3_region_change(conn)
    assert irene_region_asof(conn, "2026-02-15") == "West"
    assert irene_row(conn)[1] == "East"


def test_all_three_total_four_rows_three_current(conn):
    apply_all_three(conn)
    assert dim_row_count(conn) == 4
    assert current_view(conn) == [
        ("David Kim", "Sales", 96000, "East"),
        ("Frank Lopez", "Data", 115000, "West"),
        ("Irene Novak", "Sales", 175000, "West"),
    ]


def test_asof_frank_flips_on_effective_date(conn):
    apply_all_three(conn)
    feb = as_of(conn, "2026-02-15")
    mar = as_of(conn, "2026-03-15")
    assert len(feb) == 3 and len(mar) == 3
    assert feb[1] == ("Frank Lopez", "Sales", 98000, "West")
    assert mar[1] == ("Frank Lopez", "Data", 115000, "West")


def test_asof_shows_type1_rewrite_and_type3_overwrite(conn):
    apply_all_three(conn)
    # David shows $96,000 even in February (he was paid $95,000);
    # Irene shows West even in February (she was East).
    feb = as_of(conn, "2026-02-15")
    assert feb[0] == ("David Kim", "Sales", 96000, "East")
    assert feb[2] == ("Irene Novak", "Sales", 175000, "West")


def test_merge_batch_five_rows_four_current(conn):
    apply_merge_batch(conn)
    assert batch_totals(conn) == (5, 4)
    assert grace_row(conn) == ("Engineering", "West", 190000, "2026-03-01")


def test_merge_batch_matches_individual_changes(conn):
    apply_merge_batch(conn)
    assert frank_rows(conn) == [
        ("Sales", 98000, "2026-01-01", "2026-03-01", 0),
        ("Data", 115000, "2026-03-01", "9999-12-31", 1),
    ]
    assert david_salary(conn) == 96000
    assert irene_row(conn) == ("West", "East", 175000, "2026-01-01")


def test_merge_sql_names_all_four_cases(conn):
    assert "WHEN MATCHED AND source.change_type = 'type1'" in MERGE_SQL
    assert "WHEN MATCHED AND source.change_type = 'type2'" in MERGE_SQL
    assert "WHEN MATCHED AND source.change_type = 'type3'" in MERGE_SQL
    assert "WHEN NOT MATCHED THEN" in MERGE_SQL
    # The honest limit is stated in the SQL comment, not hidden.
    assert "cannot both close" in MERGE_SQL


def test_staging_table_holds_four_rows(conn):
    assert conn.execute("SELECT COUNT(*) FROM stg_employee_changes").fetchone()[0] == 4
    types = conn.execute(
        "SELECT change_type FROM stg_employee_changes ORDER BY employee_id"
    ).fetchall()
    assert [t[0] for t in types] == ["new", "type1", "type2", "type3"]
