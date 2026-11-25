"""Day 48 tests: SQL incremental models and watermarking.

Same company database as Days 35–47, plus order_events (10 rows),
load_state and mart_daily_sales (both start empty). All expected
numbers were computed against the seed and checked by hand:
full rebuild 10 rows $102,000; load 1 (arrived by Feb 12 18:00)
6 events $72,000, watermark '2026-02-12 13:30'; naive load 2
3 events $26,000, mart 9 rows $98,000, event 9 ($4,000) missing;
lookback 3 days 6 events $42,000, mart 10 rows $102,000 after
the fix, watermark '2026-02-18 15:45'.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_full_rebuild import (
    full_rebuild,
    mart_row_count,
    mart_rows,
    mart_total,
    source_total,
)
from problem_02_watermark import (
    load_1,
    load_1_event_count,
    load_1_total,
    load_1_watermark,
    watermark,
)
from problem_03_incremental_load import (
    boundary_row_count,
    incremental_event_count,
    incremental_load,
    incremental_total,
    mart_total_after_load_2,
)
from problem_04_late_row import (
    event_in_mart,
    late_events,
    mart_shortfall,
)
from problem_05_lookback_fix import (
    lookback_cutoff,
    lookback_event_count,
    lookback_load,
    lookback_total,
    lookback_window_start,
)
from seed import create_company_db


@pytest.fixture
def conn():
    connection = create_company_db()
    yield connection
    connection.close()


@pytest.fixture
def loaded(conn):
    """Fresh db with load 1 done: mart 6 rows, watermark set."""
    load_1(conn)
    return conn


@pytest.fixture
def naive_loaded(conn):
    """Fresh db with loads 1+2 (naive) done: mart 9 rows, $98,000."""
    load_1(conn)
    incremental_load(conn)
    return conn


def test_seed_has_ten_events_and_empty_mart_and_state(conn):
    assert conn.execute("SELECT COUNT(*) FROM order_events").fetchone()[0] == 10
    assert conn.execute("SELECT COUNT(*) FROM mart_daily_sales").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM load_state").fetchone()[0] == 0
    assert watermark(conn) is None


def test_full_rebuild_matches_source(conn):
    full_rebuild(conn)
    assert mart_row_count(conn) == 10
    assert mart_total(conn) == 102000
    assert mart_total(conn) == source_total(conn)
    assert mart_rows(conn)[0] == ("2026-02-01", "David Kim", 12000)
    assert ("2026-02-11", "David Kim", 4000) in mart_rows(conn)


def test_load_1_loads_six_events_and_sets_watermark(loaded):
    assert load_1_event_count(loaded) == 6
    assert load_1_total(loaded) == 72000
    assert load_1_watermark(loaded) == "2026-02-12 13:30"
    assert watermark(loaded) == "2026-02-12 13:30"
    assert mart_row_count(loaded) == 6
    assert mart_total(loaded) == 72000


def test_watermark_is_none_before_first_load(conn):
    assert watermark(conn) is None


def test_incremental_load_takes_only_new_events(loaded):
    assert incremental_event_count(loaded) == 3
    assert incremental_total(loaded) == 26000
    assert incremental_load(loaded) == 3
    assert mart_row_count(loaded) == 9
    assert mart_total_after_load_2(loaded) == 98000


def test_boundary_event_is_not_reprocessed(loaded):
    incremental_load(loaded)
    assert boundary_row_count(loaded) == 1
    row = loaded.execute(
        "SELECT total FROM mart_daily_sales "
        "WHERE sale_date = '2026-02-12' AND seller = 'Irene Novak'"
    ).fetchone()
    assert row[0] == 7000


def test_late_row_is_the_only_one_missed(naive_loaded):
    assert late_events(naive_loaded) == [9]
    assert event_in_mart(naive_loaded, 9) is False
    assert event_in_mart(naive_loaded, 7) is True


def test_mart_is_4000_short_after_naive_loads(naive_loaded):
    assert mart_shortfall(naive_loaded) == 4000
    assert mart_row_count(naive_loaded) == 9


def test_lookback_window_covers_six_events(naive_loaded):
    assert lookback_cutoff(naive_loaded) == "2026-02-09 13:30:00"
    assert lookback_window_start(naive_loaded) == "2026-02-09"
    assert lookback_event_count(naive_loaded) == 6
    assert lookback_total(naive_loaded) == 42000


def test_lookback_fix_recovers_the_late_row(naive_loaded):
    lookback_load(naive_loaded)
    assert mart_row_count(naive_loaded) == 10
    assert mart_total(naive_loaded) == 102000
    assert event_in_mart(naive_loaded, 9) is True
    assert watermark(naive_loaded) == "2026-02-18 15:45"


def test_lookback_load_is_idempotent(naive_loaded):
    lookback_load(naive_loaded)
    first = mart_rows(naive_loaded)
    lookback_load(naive_loaded)
    assert mart_rows(naive_loaded) == first
    assert mart_total(naive_loaded) == 102000
    assert watermark(naive_loaded) == "2026-02-18 15:45"
