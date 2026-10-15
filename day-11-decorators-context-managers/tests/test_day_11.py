"""Day 11 tests — every solution must pass before the day is committed."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_wrap_the_flaky_call import ApiTimeout, retry
from problem_02_backoff_not_hammering import backoff_delay, retry_backoff
from problem_03_time_every_stage import FakeClock, StageTimer, timer
from problem_04_with_blocks import (
    FakeConnection,
    managed_connection,
    managed_connection_gen,
)
from problem_05_retry_never_leaks import FakePool, build_pipeline


# --- Problem 1: retry ---------------------------------------------------------

def _flaky_factory(failures, exc=ApiTimeout):
    calls = []

    @retry(max_attempts=3, exceptions=(ApiTimeout,))
    def go():
        calls.append(1)
        if len(calls) <= failures:
            raise exc("boom")
        return "ok"

    return go, calls


def test_01_succeeds_first_try_single_call():
    go, calls = _flaky_factory(0)
    assert go() == "ok"
    assert len(calls) == 1


def test_01_fails_twice_then_succeeds():
    go, calls = _flaky_factory(2)
    assert go() == "ok"
    assert len(calls) == 3


def test_01_exhausted_raises_last_original_exception():
    go, calls = _flaky_factory(5)
    with pytest.raises(ApiTimeout):
        go()
    assert len(calls) == 3  # exactly max_attempts, no more


def test_01_unlisted_exception_not_retried():
    go, calls = _flaky_factory(5, exc=ValueError)

    @retry(max_attempts=3, exceptions=(ApiTimeout,))
    def go2():
        calls.append(1)
        raise ValueError("bad input — a bug, not a timeout")

    with pytest.raises(ValueError):
        go2()
    assert len(calls) == 1


def test_01_keyboard_interrupt_never_swallowed():
    @retry(max_attempts=3)
    def go():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        go()


def test_01_wraps_preserves_name_and_doc():
    @retry(max_attempts=2)
    def fetch_batch(batch_id):
        """Fetches one batch."""
        return batch_id

    assert fetch_batch.__name__ == "fetch_batch"
    assert fetch_batch.__doc__ == "Fetches one batch."


def test_01_zero_attempts_rejected():
    with pytest.raises(ValueError):
        retry(max_attempts=0)


# --- Problem 2: backoff --------------------------------------------------------

def test_02_geometric_growth():
    assert [backoff_delay(a, base=1.0) for a in range(4)] == [1.0, 2.0, 4.0, 8.0]


def test_02_cap_clips():
    assert [backoff_delay(a, base=10.0, cap=30.0) for a in range(4)] == [
        10.0, 20.0, 30.0, 30.0]


def test_02_jitter_stays_in_band():
    d = backoff_delay(2, base=1.0, jitter=1.0, rng=lambda: 0.5)
    assert d == pytest.approx(2.0)  # 4.0 * ((1-1) + 1*0.5)


def test_02_retry_sleeps_backoff_between_attempts():
    sleeps, calls = [], []

    @retry_backoff(max_attempts=4, base=1.0, exceptions=(ApiTimeout,),
                   sleep=sleeps.append)
    def go():
        calls.append(1)
        if len(calls) < 4:
            raise ApiTimeout("sick")
        return "ok"

    assert go() == "ok"
    assert sleeps == [1.0, 2.0, 4.0]


def test_02_exhausted_raises_after_last_attempt_no_extra_sleep():
    sleeps = []

    @retry_backoff(max_attempts=3, base=1.0, exceptions=(ApiTimeout,),
                   sleep=sleeps.append)
    def go():
        raise ApiTimeout("down")

    with pytest.raises(ApiTimeout):
        go()
    assert sleeps == [1.0, 2.0]  # sleeps only BETWEEN attempts


# --- Problem 3: timer ----------------------------------------------------------

def test_03_records_duration_on_success():
    clock, reg = FakeClock(step=2.0), StageTimer()

    @timer("extract", reg, clock)
    def extract():
        return 1

    assert extract() == 1
    assert reg.durations["extract"] == [2.0]


def test_03_records_and_reraises_on_exception():
    clock, reg = FakeClock(step=0.5), StageTimer()

    @timer("load", reg, clock)
    def load():
        raise RuntimeError("warehouse down")

    with pytest.raises(RuntimeError):
        load()
    assert reg.durations["load"] == [0.5]  # evidence survives the throw


def test_03_stages_tracked_separately_as_lists():
    clock, reg = FakeClock(step=1.0), StageTimer()

    @timer("a", reg, clock)
    def a():
        pass

    @timer("b", reg, clock)
    def b():
        pass

    a(); a(); b()
    assert reg.durations == {"a": [1.0, 1.0], "b": [1.0]}
    assert reg.total("a") == 2.0


def test_03_wraps_preserves_stage_name():
    @timer("extract", StageTimer(), FakeClock())
    def extract_orders():
        """Pulls orders."""

    assert extract_orders.__name__ == "extract_orders"


# --- Problem 4: context managers ------------------------------------------------

def test_04_clean_exit_commits_and_closes():
    with managed_connection() as conn:
        pass
    assert (conn.committed, conn.rolled_back, conn.closed) == (1, 0, 1)


def test_04_exception_rolls_back_closes_and_propagates():
    with pytest.raises(RuntimeError):
        with managed_connection() as conn:
            raise RuntimeError("mid-batch failure")
    assert (conn.committed, conn.rolled_back, conn.closed) == (0, 1, 1)


def test_04_generator_form_same_contract():
    with managed_connection_gen() as conn:
        pass
    assert (conn.committed, conn.rolled_back, conn.closed) == (1, 0, 1)

    with pytest.raises(RuntimeError):
        with managed_connection_gen() as conn2:
            raise RuntimeError("x")
    assert (conn2.committed, conn2.rolled_back, conn2.closed) == (0, 1, 1)


# --- Problem 5: retry outside, with inside --------------------------------------

def test_05_retry_recovers_and_each_attempt_closes():
    pool, sleeps = FakePool(), []
    extract = build_pipeline(["f", "f"], pool, sleeps)

    assert extract(7) == ["row-7-a", "row-7-b"]
    assert len(pool.connections) == 3                      # one per attempt
    assert all(c.closed == 1 for c in pool.connections)    # none leak
    assert [c.rolled_back for c in pool.connections] == [1, 1, 0]
    assert [c.committed for c in pool.connections] == [0, 0, 1]
    assert sleeps == [1.0, 2.0]                            # backoff between


def test_05_all_fail_raises_with_every_connection_closed():
    pool, sleeps = FakePool(), []
    extract = build_pipeline(["f", "f", "f"], pool, sleeps)

    with pytest.raises(ApiTimeout):
        extract(7)
    assert len(pool.connections) == 3
    assert all(c.closed == 1 and c.rolled_back == 1
               for c in pool.connections)
    assert all(c.committed == 0 for c in pool.connections)


def test_05_bug_not_retried_but_connection_still_closed():
    pool, sleeps = FakePool(), []
    extract = build_pipeline([], pool, sleeps)

    with pytest.raises(ValueError):
        extract(-1)   # bad batch id: a bug, not a timeout
    assert len(pool.connections) == 1   # single attempt, still closed
    assert pool.connections[0].closed == 1
    assert sleeps == []                 # no backoff — nothing retried
