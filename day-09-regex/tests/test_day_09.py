"""Day 9 tests — every solution must pass before the day is committed."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_find_vs_anchor import find_error_code
from problem_02_named_groups import parse_log_line
from problem_03_greedy_vs_lazy import first_bracketed
from problem_04_readable_pattern import parse_access_log
from problem_05_backtracking_guard import validate_token


# --- Problem 1: find_error_code ----------------------------------------------

def test_01_finds_code_buried_mid_line():
    assert find_error_code(
        "2026-10-12 09:14:02 svc=auth request_id=abc-123 ERROR-5042 upstream timeout"
    ) == 5042


def test_01_is_case_insensitive():
    assert find_error_code("disk error-17 on node 4") == 17


def test_01_returns_none_when_absent():
    assert find_error_code("all clear, nothing to see") is None
    assert find_error_code("") is None
    assert find_error_code(None) is None


def test_01_takes_first_code_only():
    assert find_error_code("ERROR-1 then ERROR-2") == 1


# --- Problem 2: parse_log_line -----------------------------------------------

def test_02_parses_full_shape_with_service_tag():
    out = parse_log_line("2026-10-12 09:14:02 ERROR [auth] login failed for user jdoe")
    assert out == {
        "ts": "2026-10-12 09:14:02",
        "level": "ERROR",
        "service": "auth",
        "msg": "login failed for user jdoe",
    }


def test_02_handles_missing_service_tag_and_zulu_ts():
    out = parse_log_line("2026-10-12T09:14:02Z WARN disk at 91%")
    assert out["level"] == "WARN"
    assert out["service"] is None
    assert out["msg"] == "disk at 91%"


def test_02_returns_none_on_non_log_line():
    assert parse_log_line("not a log line at all") is None
    assert parse_log_line(None) is None


def test_02_msg_keeps_brackets_and_spaces():
    out = parse_log_line("2026-10-12 09:14:02 INFO [etl] wrote [1,000] rows ok")
    assert out["msg"] == "wrote [1,000] rows ok"


# --- Problem 3: first_bracketed ------------------------------------------------

def test_03_returns_first_tag_not_greedy_span():
    assert first_bracketed("tags: [ingest] stage [parse] failed") == "ingest"


def test_03_returns_none_when_no_brackets():
    assert first_bracketed("nothing bracketed here") is None


def test_03_refuses_nested_brackets_loudly():
    with pytest.raises(ValueError):
        first_bracketed("broken [a [b] c] nesting")


def test_03_empty_brackets_yield_empty_string():
    assert first_bracketed("marker [] end") == ""


# --- Problem 4: parse_access_log ----------------------------------------------

def test_04_parses_standard_access_line():
    out = parse_access_log("203.0.113.7 - 200 GET /api/events")
    assert out == {"ip": "203.0.113.7", "code": 200,
                   "method": "GET", "path": "/api/events"}


def test_04_code_is_int_and_method_varies():
    out = parse_access_log("10.0.0.9 - 500 POST /api/ingest")
    assert out["code"] == 500 and isinstance(out["code"], int)
    assert out["method"] == "POST"


def test_04_returns_none_on_garbage():
    assert parse_access_log("garbage in") is None
    assert parse_access_log("203.0.113.7 - 200 SMOKE /x") is None


def test_04_rejects_malformed_ip():
    assert parse_access_log("999.0.113 - 200 GET /x") is None


# --- Problem 5: validate_token -------------------------------------------------

def test_05_accepts_plain_tokens():
    assert validate_token("batch 42 ok") is True
    assert validate_token("hello_world") is True


def test_05_rejects_bad_characters():
    assert validate_token("batch-42!") is False
    assert validate_token("") is False
    assert validate_token(None) is False


def test_05_length_guard_fires_before_regex():
    assert validate_token("a" * 201) is False
    assert validate_token("a" * 200) is True


def test_05_adversarial_input_returns_instantly():
    start = time.perf_counter()
    assert validate_token("!" * 200) is False
    assert validate_token(("ab " * 67)[:200]) is True
    assert time.perf_counter() - start < 2.0  # the flat pattern is linear
