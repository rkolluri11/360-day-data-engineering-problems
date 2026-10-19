"""Day 16 tests — every solution must pass before the day is committed.

The suite practices what the day preaches: concurrency asserted
deterministically. No timing bets, no flaky races — barriers and
events force the interleavings instead of praying for them.
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_pick_the_model import (
    ASYNCIO,
    ASYNCIO_THRESHOLD,
    CPU_BOUND,
    IO_BOUND,
    PROCESSES,
    THREADS,
    explain,
    pick_model,
)
from problem_02_threaded_fanout import fetch_all
from problem_03_process_pool_cpu import hash_records, sha256_record
from problem_04_asyncio_fanout import fetch_all_async
from problem_05_wrong_model_traps import (
    RacyCounter,
    SafeCounter,
    diagnose,
)


# --- Problem 1: pick the model -------------------------------------------------

@pytest.mark.parametrize("count", [1, 8, 500])
def test_cpu_bound_always_means_processes(count):
    assert pick_model(CPU_BOUND, count) == PROCESSES


@pytest.mark.parametrize("count", [1, 50, ASYNCIO_THRESHOLD - 1])
def test_small_io_bound_means_threads(count):
    assert pick_model(IO_BOUND, count) == THREADS


@pytest.mark.parametrize("count", [ASYNCIO_THRESHOLD, 5000])
def test_huge_io_bound_means_asyncio(count):
    assert pick_model(IO_BOUND, count) == ASYNCIO


def test_every_model_has_an_explanation():
    for model in (THREADS, PROCESSES, ASYNCIO):
        assert explain(model).strip(), model


# --- Problem 2: threaded fan-out ----------------------------------------------

def _blocking_fetch_factory():
    """A fake I/O fetch that blocks until the test releases it, while
    tracking how many workers overlap — deterministic by construction."""
    state = {"in_flight": 0, "peak": 0}
    lock = threading.Lock()
    release = threading.Event()

    def fake_fetch(item):
        with lock:
            state["in_flight"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
        assert release.wait(timeout=10), "worker starved — test bug"
        with lock:
            state["in_flight"] -= 1
        return item * 10

    return fake_fetch, state, lock, release


def test_threaded_fanout_runs_concurrently_within_bound():
    fake_fetch, state, lock, release = _blocking_fetch_factory()
    box = {}

    def run():
        box["results"] = fetch_all(fake_fetch, list(range(12)), max_workers=4)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            with lock:
                if state["in_flight"] >= 2:
                    break
            time.sleep(0.01)
        release.set()
        worker.join(timeout=10)
        assert not worker.is_alive(), "fan-out did not finish"
    finally:
        release.set()
    assert state["peak"] <= 4, "pool exceeded max_workers"
    assert state["peak"] >= 2, "no overlap observed — not actually concurrent"
    assert box["results"] == [(True, i * 10) for i in range(12)]


def test_threaded_fanout_captures_errors_per_item():
    def flaky(item):
        if item == "bad":
            raise ValueError("bad row")
        return item.upper()

    results = fetch_all(flaky, ["a", "bad", "c"], max_workers=2)
    assert results[0] == (True, "A")
    assert results[2] == (True, "C")
    ok, exc = results[1]
    assert ok is False and isinstance(exc, ValueError)


def test_threaded_fanout_preserves_input_order():
    def slow(item):
        time.sleep(0.02 if item % 2 else 0.001)  # odd items finish last
        return item

    results = fetch_all(slow, list(range(10)), max_workers=5)
    assert [value for ok, value in results] == list(range(10))
    assert all(ok for ok, _ in results)


# --- Problem 3: process pool ----------------------------------------------------

def test_process_pool_matches_serial_hashes():
    records = [{"id": f"u-{i}", "amount": f"{i}.50"} for i in range(20)]
    assert hash_records(records, max_workers=2) == [sha256_record(r) for r in records]


def test_process_pool_preserves_order():
    records = [{"n": i} for i in range(10)]
    assert hash_records(records, max_workers=4) == [sha256_record(r) for r in records]


def test_unpicklable_worker_fails_loudly_at_submit():
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(max_workers=1) as pool:
        with pytest.raises(Exception, match="[Pp]ickle"):
            pool.submit(lambda x: x, 1).result()


# --- Problem 4: asyncio fan-out --------------------------------------------------

def test_asyncio_fanout_bounds_concurrency_and_preserves_order():
    state = {"in_flight": 0, "peak": 0}

    async def fake_fetch(item):
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        await asyncio.sleep(0.01)
        state["in_flight"] -= 1
        return item * 3

    results = asyncio.run(fetch_all_async(fake_fetch, list(range(30)), limit=10))
    assert results == [i * 3 for i in range(30)]
    assert state["peak"] == 10, "semaphore did not bound concurrency exactly"


def test_asyncio_fanout_is_fail_fast_by_default():
    async def flaky(item):
        if item == 2:
            raise RuntimeError("boom")
        return item

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(fetch_all_async(flaky, [0, 1, 2, 3], limit=4))


# --- Problem 5: wrong-model traps -------------------------------------------------

@pytest.mark.parametrize(
    "model,kind,count,fragment",
    [
        (THREADS, CPU_BOUND, 8, "GIL stall"),
        (PROCESSES, IO_BOUND, 20, "Spawn cost"),
        (ASYNCIO, CPU_BOUND, 4, "Loop freeze"),
    ],
)
def test_diagnose_flags_wrong_pairings(model, kind, count, fragment):
    warning = diagnose(model, kind, count)
    assert warning and fragment in warning


@pytest.mark.parametrize(
    "model,kind,count",
    [
        (PROCESSES, CPU_BOUND, 8),
        (THREADS, IO_BOUND, 50),
        (ASYNCIO, IO_BOUND, 5000),
        (PROCESSES, IO_BOUND, 5000),  # big I/O counts amortize spawn cost
    ],
)
def test_diagnose_stays_quiet_on_right_pairings(model, kind, count):
    assert diagnose(model, kind, count) is None


def test_racy_counter_loses_an_update_deterministically():
    counter = RacyCounter()
    threads = [threading.Thread(target=counter.increment) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert counter.value == 1, "barrier interleaving should lose exactly one update"


def test_safe_counter_never_loses_an_update():
    counter = SafeCounter()
    threads = [
        threading.Thread(target=lambda: [counter.increment() for _ in range(500)])
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert counter.value == 2000
