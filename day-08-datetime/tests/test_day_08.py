"""Day 8 tests — every solution must pass before the day is committed."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_parse_iso import parse_timestamp
from problem_02_make_aware import to_utc
from problem_03_daily_buckets import bucket_by_local_date
from problem_04_event_time_windows import assign_windows
from problem_05_duration_across_dst import elapsed_seconds

CHI = "America/Chicago"
UTC = timezone.utc


# --- Problem 1: parse_timestamp ------------------------------------------------

def test_01_parses_plain_iso_as_naive():
    dt = parse_timestamp("2026-10-11T09:00:00")
    assert dt == datetime(2026, 10, 11, 9, 0, 0)
    assert dt.tzinfo is None  # parsing is rung 1; awareness is rung 2


def test_01_parses_z_suffix_as_utc():
    dt = parse_timestamp("2026-10-11T09:00:00Z")
    assert dt.utcoffset() == timedelta(0)


def test_01_keeps_numeric_offset():
    dt = parse_timestamp("2026-10-11T14:30:00+05:30")
    assert dt.utcoffset() == timedelta(hours=5, minutes=30)


def test_01_rejects_garbage_loudly():
    for bad in ["not a date", "", "   ", "2026-13-45", None, 42]:
        with pytest.raises(ValueError):
            parse_timestamp(bad)


# --- Problem 2: to_utc ----------------------------------------------------------

def test_02_stamps_naive_then_converts():
    # 9 AM Chicago in October is CDT (UTC-5) -> 14:00 UTC
    assert to_utc(datetime(2026, 10, 11, 9, 0), CHI) == \
        datetime(2026, 10, 11, 14, 0, tzinfo=UTC)


def test_02_respects_existing_zone_instead_of_overwriting():
    aware = datetime(2026, 10, 11, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert to_utc(aware, CHI) == datetime(2026, 10, 11, 3, 30, tzinfo=UTC)


def test_02_result_is_always_aware_utc():
    out = to_utc(datetime(2026, 1, 15, 12, 0), CHI)  # CST (UTC-6) in January
    assert out.tzinfo is not None and out.utcoffset() == timedelta(0)


def test_02_rejects_non_datetime():
    with pytest.raises(TypeError):
        to_utc("2026-10-11T09:00:00", CHI)


# --- Problem 3: bucket_by_local_date --------------------------------------------

def test_03_repeated_dst_hour_lands_on_one_local_date():
    stamps = [  # 00:30 CDT, 01:30 CDT (first), 01:30 CST (second) — all Nov 1
        datetime(2026, 11, 1, 5, 30, tzinfo=UTC),
        datetime(2026, 11, 1, 6, 30, tzinfo=UTC),
        datetime(2026, 11, 1, 7, 30, tzinfo=UTC),
    ]
    assert bucket_by_local_date(stamps, CHI) == {date(2026, 11, 1): 3}


def test_03_utc_midnight_trap_stays_on_local_date():
    # 04:59 UTC Nov 1 is 23:59 CDT Oct 31 — bucket by local date, not UTC date
    stamps = [datetime(2026, 11, 1, 4, 59, tzinfo=UTC)]
    assert bucket_by_local_date(stamps, CHI) == {date(2026, 10, 31): 1}


def test_03_groups_across_days():
    stamps = [
        datetime(2026, 11, 2, 6, 30, tzinfo=UTC),   # 00:30 CST Nov 2
        datetime(2026, 11, 2, 7, 30, tzinfo=UTC),   # 01:30 CST Nov 2
        datetime(2026, 11, 1, 5, 30, tzinfo=UTC),   # 00:30 CDT Nov 1
    ]
    assert bucket_by_local_date(stamps, CHI) == \
        {date(2026, 11, 2): 2, date(2026, 11, 1): 1}


def test_03_empty_in_empty_out():
    assert bucket_by_local_date([], CHI) == {}


# --- Problem 4: assign_windows -----------------------------------------------------

def test_04_groups_by_event_time_not_processing_time():
    chicago = ZoneInfo(CHI)
    events = [
        {"id": 1, "event_time": datetime(2026, 10, 11, 9, 15, tzinfo=chicago),
         "processed_at": datetime(2026, 10, 11, 9, 16, tzinfo=chicago)},
        {"id": 2, "event_time": datetime(2026, 10, 11, 9, 45, tzinfo=chicago),
         "processed_at": datetime(2026, 10, 11, 12, 5, tzinfo=chicago)},  # 3h late
        {"id": 3, "event_time": datetime(2026, 10, 11, 10, 5, tzinfo=chicago),
         "processed_at": datetime(2026, 10, 11, 10, 6, tzinfo=chicago)},
    ]
    windows = assign_windows(events)
    nine = datetime(2026, 10, 11, 14, 0, tzinfo=UTC)   # 9 AM CDT = 14:00 UTC
    ten = datetime(2026, 10, 11, 15, 0, tzinfo=UTC)
    assert sorted(e["id"] for e in windows[nine]) == [1, 2]  # late event keeps its window
    assert [e["id"] for e in windows[ten]] == [3]


def test_04_hour_boundary_goes_to_the_new_window():
    chicago = ZoneInfo(CHI)
    events = [
        {"event_time": datetime(2026, 10, 11, 10, 0, 0, tzinfo=chicago)},
        {"event_time": datetime(2026, 10, 11, 9, 59, 59, tzinfo=chicago)},
    ]
    windows = assign_windows(events)
    assert len(windows) == 2


def test_04_two_hour_windows():
    chicago = ZoneInfo(CHI)
    events = [
        {"event_time": datetime(2026, 10, 11, 9, 30, tzinfo=chicago)},
        {"event_time": datetime(2026, 10, 11, 10, 30, tzinfo=chicago)},
    ]
    windows = assign_windows(events, window_hours=2)
    assert len(windows) == 1  # both inside the 8–10 AM UTC window


def test_04_payload_survives_windowing():
    chicago = ZoneInfo(CHI)
    events = [{"event_time": datetime(2026, 10, 11, 9, 5, tzinfo=chicago),
               "amt": 500}]
    only = next(iter(assign_windows(events).values()))
    assert only[0]["amt"] == 500


# --- Problem 5: elapsed_seconds -----------------------------------------------------

def test_05_fall_back_counts_the_repeated_hour():
    # wall clock says 2h; the 1–2 AM hour happened twice -> 3h
    assert elapsed_seconds("2026-11-01T00:30:00-05:00",
                           "2026-11-01T02:30:00-06:00") == 10800.0


def test_05_spring_forward_skips_the_missing_hour():
    # wall clock says 2h; 2–3 AM never happened -> 1h
    assert elapsed_seconds("2026-03-08T01:30:00-06:00",
                           "2026-03-08T03:30:00-05:00") == 3600.0


def test_05_plain_interval_is_exact():
    assert elapsed_seconds("2026-10-11T09:00:00+00:00",
                           "2026-10-11T09:00:30+00:00") == 30.0


def test_05_naive_inputs_refuse_to_lie():
    with pytest.raises(ValueError):
        elapsed_seconds("2026-10-11T09:00:00", "2026-10-11T10:00:00")
