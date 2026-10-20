"""Day 17 tests — every solution must pass before the day is committed.

The suite practices what the day preaches: concurrency asserted
deterministically. asyncio.Events force the interleavings instead
of praying for them; assertions are about order and counts, never
about wall-clock durations.
"""

import asyncio
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_coroutine_pause import concurrent_fetch, sequential_fetch
from problem_02_gather_fanout import gather_all
from problem_03_bounded_semaphore import bounded_gather
from problem_04_to_thread import process_async, process_naive
from problem_05_backpressure_traps import safe_gather

GUARD = 10  # deadlock insurance only — never asserted against


def make_gated_fetch(log, started, gates):
    """Fetch that logs start, signals, then waits on its gate."""

    async def fetch(url):
        log.append(("start", url))
        started[url].set()
        await gates[url].wait()
        log.append(("end", url))
        return "page:" + url

    return fetch


def fresh_gates(urls):
    return (
        {u: asyncio.Event() for u in urls},
        {u: asyncio.Event() for u in urls},
    )


# --- Problem 1: coroutines pause ------------------------------------------------

def test_concurrent_fetch_interleaves():
    urls = ["a", "b", "c"]

    async def main():
        log = []
        started, gates = fresh_gates(urls)
        fetch = make_gated_fetch(log, started, gates)
        task = asyncio.create_task(concurrent_fetch(fetch, urls))
        await asyncio.wait_for(
            asyncio.gather(*(s.wait() for s in started.values())), GUARD
        )
        # all three started, none finished: they overlap
        assert [e for e in log if e[0] == "end"] == []
        for g in gates.values():
            g.set()
        results = await asyncio.wait_for(task, GUARD)
        assert results == ["page:a", "page:b", "page:c"]
        first_end = next(i for i, e in enumerate(log) if e[0] == "end")
        last_start = max(i for i, e in enumerate(log) if e[0] == "start")
        assert last_start < first_end  # every start precedes every end

    asyncio.run(main())


def test_sequential_fetch_never_overlaps():
    urls = ["a", "b"]

    async def main():
        log = []
        started, gates = fresh_gates(urls)
        fetch = make_gated_fetch(log, started, gates)
        task = asyncio.create_task(sequential_fetch(fetch, urls))
        await asyncio.wait_for(started["a"].wait(), GUARD)
        assert ("start", "b") not in log  # b cannot start while a is open
        gates["a"].set()
        await asyncio.wait_for(started["b"].wait(), GUARD)
        assert ("end", "a") in log  # a fully finished before b began
        gates["b"].set()
        results = await asyncio.wait_for(task, GUARD)
        assert results == ["page:a", "page:b"]

    asyncio.run(main())


# --- Problem 2: gather ----------------------------------------------------------

def test_gather_preserves_input_order():
    urls = ["u0", "u1", "u2"]

    async def main():
        log = []
        started, gates = fresh_gates(urls)
        fetch = make_gated_fetch(log, started, gates)
        task = asyncio.create_task(gather_all(fetch, urls))
        await asyncio.wait_for(
            asyncio.gather(*(s.wait() for s in started.values())), GUARD
        )
        # release in REVERSE latency order: u2 finishes first
        for u in reversed(urls):
            gates[u].set()
            await asyncio.sleep(0)
        results = await asyncio.wait_for(task, GUARD)
        assert results == ["page:u0", "page:u1", "page:u2"]

    asyncio.run(main())


def test_gather_fail_fast():
    async def fetch(url):
        if url == "bad":
            raise ValueError("boom")
        return "page:" + url

    async def main():
        with pytest.raises(ValueError):
            await gather_all(fetch, ["ok1", "bad", "ok2"])

    asyncio.run(main())


def test_gather_empty_is_noop():
    async def fetch(url):  # pragma: no cover — never called
        raise AssertionError("must not be called")

    assert asyncio.run(gather_all(fetch, [])) == []


# --- Problem 3: semaphore -------------------------------------------------------

def make_tracked_fetch(log, state):
    async def fetch(url):
        state["cur"] += 1
        state["peak"] = max(state["peak"], state["cur"])
        log.append(("start", url))
        if state["cur"] == state["limit"]:
            state["full"].set()
        await state["release"].wait()
        state["cur"] -= 1
        log.append(("end", url))
        return "page:" + url

    return fetch


def test_semaphore_caps_concurrency():
    urls = ["u%d" % i for i in range(6)]
    limit = 2

    async def main():
        log = []
        state = {"cur": 0, "peak": 0, "limit": limit,
                 "full": asyncio.Event(), "release": asyncio.Event()}
        fetch = make_tracked_fetch(log, state)
        task = asyncio.create_task(bounded_gather(fetch, urls, limit))
        await asyncio.wait_for(state["full"].wait(), GUARD)
        # exactly `limit` in flight; the rest cannot start — semaphore-held
        assert [e for e in log if e[0] == "start"] == [
            ("start", "u0"), ("start", "u1")]
        state["release"].set()
        results = await asyncio.wait_for(task, GUARD)
        assert results == ["page:" + u for u in urls]
        assert state["peak"] == limit

    asyncio.run(main())


def test_semaphore_limit_one_is_serial():
    urls = ["a", "b", "c"]

    async def main():
        log = []
        state = {"cur": 0, "peak": 0, "limit": 1,
                 "full": asyncio.Event(), "release": asyncio.Event()}
        fetch = make_tracked_fetch(log, state)
        task = asyncio.create_task(bounded_gather(fetch, urls, 1))
        await asyncio.wait_for(state["full"].wait(), GUARD)
        assert [e for e in log if e[0] == "start"] == [("start", "a")]
        state["release"].set()
        results = await asyncio.wait_for(task, GUARD)
        assert results == ["page:a", "page:b", "page:c"]
        assert state["peak"] == 1

    asyncio.run(main())


# --- Problem 4: to_thread --------------------------------------------------------

def test_to_thread_keeps_loop_free():
    async def main():
        log = []
        release = threading.Event()

        async def looper():
            for _ in range(3):
                log.append(("looper_tick",))
                await asyncio.sleep(0)

        task = asyncio.create_task(process_async(["b1"], log, release))
        while ("parse_start", "b1") not in log:
            await asyncio.sleep(0)  # loop free -> worker thread starts parsing
        await looper()  # ticks WHILE the parse is still blocked on release
        release.set()
        results = await asyncio.wait_for(task, GUARD)
        assert results == ["B1"]
        first_tick = log.index(("looper_tick",))
        parse_end = log.index(("parse_end", "b1"))
        assert first_tick < parse_end  # loop ran during the blocking parse

    asyncio.run(asyncio.wait_for(main(), GUARD))


def test_naive_call_freezes_loop():
    async def main():
        log = []
        release = threading.Event()

        async def looper():
            for _ in range(3):
                log.append(("looper_tick",))
                await asyncio.sleep(0)

        loop_task = asyncio.create_task(looper())
        # the blocked loop thread cannot release itself: a helper thread does
        threading.Timer(0.3, release.set).start()
        results = await process_naive(["b1"], log, release)
        await asyncio.wait_for(loop_task, GUARD)
        assert results == ["B1"]
        parse_end = log.index(("parse_end", "b1"))
        first_tick = log.index(("looper_tick",))
        assert parse_end < first_tick  # nothing ticked until the block lifted

    asyncio.run(asyncio.wait_for(main(), GUARD))


# --- Problem 5: backpressure traps ----------------------------------------------

def test_safe_gather_quarantines_each_failure():
    urls = ["ok1", "slow", "bad", "ok2"]

    async def main():
        log = []
        started, gates = fresh_gates(["ok1", "ok2"])

        async def fetch(url):
            if url == "slow":
                await asyncio.sleep(3600)  # hangs: timeout must fire first
            if url == "bad":
                raise RuntimeError("boom")
            log.append(("start", url))
            started[url].set()
            await gates[url].wait()
            return "page:" + url

        task = asyncio.create_task(safe_gather(fetch, urls, 2, 0.05))
        await asyncio.wait_for(started["ok1"].wait(), GUARD)
        gates["ok1"].set()
        await asyncio.wait_for(started["ok2"].wait(), GUARD)
        gates["ok2"].set()
        results = await asyncio.wait_for(task, GUARD)

        assert [r[0] for r in results] == urls  # order preserved
        assert results[0] == ("ok1", "ok", "page:ok1")
        assert results[1][0] == "slow" and results[1][1] == "timeout"
        assert isinstance(results[1][2], asyncio.TimeoutError)
        assert results[2][0] == "bad" and results[2][1] == "error"
        assert isinstance(results[2][2], RuntimeError)
        assert results[3] == ("ok2", "ok", "page:ok2")

    asyncio.run(main())


def test_safe_gather_all_ok_when_healthy():
    async def fetch(url):
        await asyncio.sleep(0)
        return "page:" + url

    async def main():
        return await safe_gather(fetch, ["a", "b", "c"], limit=10, timeout=5)

    results = asyncio.run(main())
    assert results == [("a", "ok", "page:a"), ("b", "ok", "page:b"),
                       ("c", "ok", "page:c")]
