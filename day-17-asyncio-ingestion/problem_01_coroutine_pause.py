"""Problem 1 — coroutines pause: sequential vs concurrent fetch
=============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
An ``async def`` function is a COROUTINE: calling it runs nothing,
it just builds the coroutine object. It only runs when AWAITED —
and at every ``await`` it can PAUSE, letting the event loop run
someone else, then resume when the I/O completes.

So the same fetch loop has two very different shapes:

    # sequential: page 2 waits for page 1 to fully finish
    results = [await fetch(u) for u in urls]

    # concurrent: all pages are in flight at once
    tasks = [asyncio.create_task(fetch(u)) for u in urls]
    results = [await t for t in tasks]

Plain words: sequential is reading books one at a time; concurrent
is starting all the laundry loads, then folding as each finishes.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
``asyncio.gather`` (Day 17 rung 3) is the production shape of
``concurrent_fetch`` below. Two traps from this file show up in
real pipelines:

  - Forgetting ``await`` on a coroutine: the fetch never runs,
    you gather a list of coroutine objects, and everything
    silently returns nothing. ``asyncio`` even warns you —
    "coroutine was never awaited".
  - Assuming ``[await t for t in tasks]`` is slow: it is not.
    The tasks already ran concurrently once created; awaiting
    in order just collects results in order. Creation is the
    fan-out, awaiting is the collection.

Your solution: ``sequential_fetch`` and ``concurrent_fetch`` are
already written. The tests force the interleavings with events —
no timing bets — and prove the difference is real.

ANALOGY
-------
Sequential is one cashier serving one customer start-to-finish.
Concurrent is the same cashier taking everyone's order first,
then handing out drinks as each machine finishes.
"""
import asyncio


async def sequential_fetch(fetch, urls):
    """Fetch each url one at a time; page 2 never starts before page 1 ends."""
    return [await fetch(u) for u in urls]


async def concurrent_fetch(fetch, urls):
    """Start every fetch, then collect; all urls are in flight together."""
    tasks = [asyncio.create_task(fetch(u)) for u in urls]
    return [await t for t in tasks]
