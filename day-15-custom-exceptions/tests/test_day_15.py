"""Day 15 tests — every solution must pass before the day is committed.

The suite practices what the day preaches: the exception taxonomy under
test, asserted with the repo's pytest convention (fixtures for shared
rows, parametrize tables for the routing matrix).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_base_error import (
    FatalError,
    PipelineError,
    RowError,
    StageError,
    fail_row,
    is_pipeline_error,
)
from problem_02_severity_hierarchy import HALT, QUARANTINE, RETRY, route_error
from problem_03_errors_carry_context import DetailedRowError, fail_parse
from problem_04_except_is_a_router import clean_batch
from problem_05_transient_vs_permanent import (
    FlakySource,
    PermanentError,
    TransientError,
    backoff_delay,
    parse_amount,
    run_with_retry,
)


# --- shared fixtures ---------------------------------------------------------

@pytest.fixture
def rows():
    return [
        {"id": "u-1", "amount": "10.50"},
        {"id": "u-2", "amount": "$1,200.00"},
        {"id": "u-3", "amount": "abc"},        # bad row
        {"id": "u-4", "amount": "(45.00)"},
    ]


@pytest.fixture
def sleeps():
    """Recorded backoff delays — no real sleeping in the suite."""
    recorded = []
    return recorded, recorded.append


# --- Problem 1: one base error -----------------------------------------------

@pytest.mark.parametrize("cls", [RowError, StageError, FatalError])
def test_taxonomy_wears_the_badge(cls):
    assert issubclass(cls, PipelineError)
    assert is_pipeline_error(cls("boom"))


def test_except_pipeline_error_catches_the_taxonomy_not_the_world():
    caught = []
    for exc in (RowError("r"), StageError("s"), FatalError("f")):
        try:
            raise exc
        except PipelineError as e:
            caught.append(type(e).__name__)
    assert caught == ["RowError", "StageError", "FatalError"]
    with pytest.raises(ValueError):
        try:
            raise ValueError("stranger")
        except PipelineError:
            pass  # a stranger must NOT be caught by the badge


def test_fail_row_raises_row_error():
    with pytest.raises(RowError):
        fail_row("missing id")


# --- Problem 2: the routing table --------------------------------------------

@pytest.mark.parametrize(
    "exc,fate",
    [
        (RowError("bad row"), QUARANTINE),
        (StageError("source down"), RETRY),
        (FatalError("dead"), HALT),
        (TransientError("busy"), RETRY),  # subclass inherits its fate
    ],
)
def test_router_maps_severity_to_fate(exc, fate):
    assert route_error(exc) == fate


def test_router_refuses_to_guess():
    with pytest.raises(TypeError):
        route_error(ValueError("not in the taxonomy"))


# --- Problem 3: errors carry context ------------------------------------------

def test_error_names_the_culprit(rows):
    with pytest.raises(DetailedRowError) as ei:
        fail_parse(rows[2], "bad amount 'abc'")
    err = ei.value
    assert "u-3" in str(err)
    assert "parse" in str(err)
    assert err.row["id"] == "u-3"
    assert err.stage == "parse"
    assert err.reason == "bad amount 'abc'"
    assert "attempt 1" in err.label()


def test_detailed_row_error_is_still_a_row_error():
    err = DetailedRowError({"id": "u-9"}, stage="load", reason="dup key")
    assert isinstance(err, RowError)
    assert route_error(err) == QUARANTINE


# --- Problem 4: the except clause is a router --------------------------------

def _upper_id(row):
    if "id" not in row or not row["id"]:
        raise RowError("missing id")
    return {**row, "id": row["id"].upper()}


def test_bad_rows_quarantine_with_a_reason(rows):
    bad = {"id": "", "amount": "1.00"}
    clean, quarantined = clean_batch(rows[:2] + [bad], _upper_id)
    assert len(clean) == 2
    assert len(quarantined) == 1
    assert quarantined[0]["_reason"] == "missing id"
    assert len(rows[:2] + [bad]) == len(clean) + len(quarantined)  # receipt balances


def test_stage_errors_escalate_past_the_budget():
    def always_down(row):
        raise StageError("source unreachable")

    with pytest.raises(FatalError) as ei:
        clean_batch([{"id": f"u-{i}"} for i in range(3)], always_down, error_budget=2)
    assert "budget 2" in str(ei.value)
    # the fatal error chains the stage errors that triggered it
    assert isinstance(ei.value.__context__, StageError)


def test_fatal_error_stops_the_line_immediately():
    def fatal_midway(row):
        if row["id"] == "u-2":
            raise FatalError("disk full")
        return row

    with pytest.raises(FatalError):
        clean_batch([{"id": "u-1"}, {"id": "u-2"}, {"id": "u-3"}], fatal_midway)


# --- Problem 5: transient vs permanent ----------------------------------------

@pytest.mark.parametrize(
    "attempt,want", [(0, 1.0), (1, 2.0), (2, 4.0), (3, 8.0)]
)
def test_backoff_doubles(attempt, want):
    assert backoff_delay(attempt, base=1.0) == want


def test_backoff_is_capped():
    assert backoff_delay(10, base=1.0, cap=60.0) == 60.0


def test_transient_errors_earn_backoff(sleeps):
    recorded, sleep = sleeps
    source = FlakySource(payload="data", fail_times=2)
    result, attempts = run_with_retry(source.fetch, max_attempts=4, sleep=sleep)
    assert result == "data"
    assert attempts == 3
    assert recorded == [1.0, 2.0]


def test_permanent_errors_get_zero_retries(sleeps):
    recorded, sleep = sleeps
    calls = []

    def bad_schema():
        calls.append(1)
        raise PermanentError("column renamed upstream")

    with pytest.raises(PermanentError):
        run_with_retry(bad_schema, sleep=sleep)
    assert len(calls) == 1
    assert recorded == []  # never slept — garbage is never retried


def test_giving_up_after_max_attempts(sleeps):
    recorded, sleep = sleeps
    source = FlakySource(payload="data", fail_times=99)
    with pytest.raises(TransientError):
        run_with_retry(source.fetch, max_attempts=3, sleep=sleep)
    assert recorded == [1.0, 2.0]  # two sleeps, then the error escapes


@pytest.mark.parametrize(
    "raw,want",
    [("10.50", 10.50), ("$1,200.00", 1200.00), ("(45.00)", -45.00), (None, None)],
)
def test_parse_amount_happy_path(raw, want):
    assert parse_amount(raw) == want


def test_parse_amount_garbage_is_permanent():
    with pytest.raises(PermanentError):
        parse_amount("abc")


def test_end_to_end_stage(rows, sleeps):
    """Parse amounts: garbage quarantines immediately, flaky source retries."""
    recorded, sleep = sleeps

    def parse_stage(row):
        try:
            return {**row, "amount": parse_amount(row["amount"])}
        except PermanentError as e:
            raise DetailedRowError(row, stage="parse", reason=str(e)) from e

    source = FlakySource(payload=rows, fail_times=1)
    fetched, _ = run_with_retry(source.fetch, max_attempts=3, sleep=sleep)
    clean, quarantined = clean_batch(fetched, parse_stage)
    assert [r["id"] for r in clean] == ["u-1", "u-2", "u-4"]
    assert [r["id"] for r in quarantined] == ["u-3"]
    assert "bad amount" in quarantined[0]["_reason"]
