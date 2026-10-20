"""Problem 2 — gather: fan out with asyncio.gather
================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``asyncio.gather`` takes a pile of coroutines and runs them all
at once on the one event loop:

    pages = await asyncio.gather(*(fetch(u) for u in urls))

One line replaces the create-tasks-then-collect dance. And the
killer feature: ``pages[i]`` always belongs to ``urls[i]`` —
gather preserves INPUT ORDER even when the network shuffles the
finish order. No index bookkeeping downstream.

Plain words: gather is the group order at the barista rail —
drinks finish in random order, but your name is still on yours.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - gather is FAIL-FAST by default: the first exception
    propagates immediately to the caller. The other coroutines
    keep running in the background — orphaned, still spending
    your API quota, still writing wherever they write. If one
    bad page must not kill the batch, pass
    ``return_exceptions=True`` and inspect each result (see
    problem 5 for the quarantine pattern from Day 15).
  - Passing the SAME coroutine object twice, or re-awaiting a
    finished gather's tasks, raises "cannot reuse already
    awaited coroutine". Build fresh coroutines per gather call.
  - ``gather(*[])`` with zero coroutines returns ``[]``
    immediately — your fan-out over an empty partition list is
    a no-op, not an error. Code for it.

Your solution: ``gather_all`` below is already written. The
tests shuffle latencies with events (not timers) and prove the
order guarantee holds.

ANALOGY
-------
asyncio.gather is a wedding photographer shouting "everyone in
the frame" — one shutter press, every face captured, and the
seating chart (input order) is how the prints come back.
"""
import asyncio


async def gather_all(fetch, urls):
    """Await fetch(url) for every url concurrently; results match url order.

    Fail-fast: the first exception propagates (wrap with
    return_exceptions=True when you need per-item quarantine —
    see problem_05_backpressure_traps).
    """
    return list(await asyncio.gather(*(fetch(u) for u in urls)))
