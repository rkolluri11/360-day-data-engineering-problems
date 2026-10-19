"""Problem 4 — asyncio fan-out: thousands of waiters, one thread
===============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Threads are cheap, but not free: 10,000 threads means 10,000
stacks and a scheduler working overtime. asyncio runs ONE
thread and one event loop; each task is a coroutine that YIELDS
while waiting on I/O, so 10,000 concurrent fetches cost one
thread's worth of memory.

``asyncio.gather`` runs coroutines concurrently and returns
results in INPUT order. The ``asyncio.Semaphore`` is the
throttle: at most N coroutines inside the ``async with`` block
at once, so you fan out without DDoSing your own source.

Plain words: threads are hiring a waiter per table. Asyncio is
one brilliant waiter who takes table 4's order, pours table 7's
wine while the kitchen works, and never stands idle — plus a
bouncer (the semaphore) capping how many tables they juggle.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - One BLOCKING call poisons the loop: ``time.sleep(1)`` or
    ``requests.get`` inside a coroutine freezes all 10,000
    tasks. Use ``await asyncio.sleep`` and async clients, or
    push blocking work to ``loop.run_in_executor``.
  - ``gather`` without a semaphore is unbounded fan-out: 10,000
    simultaneous connections will trip rate limits, exhaust
    file descriptors, or get your key revoked. Always bound it.
  - ``gather`` is fail-fast by default: the first exception
    propagates and the rest keep running in the background.
    Pass ``return_exceptions=True`` when one bad item must not
    kill the batch — same quarantine instinct as Day 15.
  - Coroutines are lazy: defining ``async def`` runs nothing
    until awaited. Forgetting ``await`` is the async version
    of forgetting to call the function.

Your solution: ``fetch_all_async`` below is already written.
Read it, then run the tests: ``python -m pytest tests -q``
from the day-16 folder.

ANALOGY
-------
The event loop is an air-traffic controller with one runway:
planes (coroutines) announce "holding for fuel" and yield the
runway instead of idling on it. The semaphore is the holding
pattern cap — only so many planes circle at once.
"""

import asyncio


async def fetch_all_async(fetch_coro, items, limit=50):
    """Await fetch_coro(item) for every item, at most `limit` in flight.

    asyncio.gather preserves input order; the semaphore bounds
    concurrency so we fan out without overwhelming the source.
    Fail-fast: the first exception propagates (see return_exceptions
    in the docstring above when you need quarantine instead).
    """
    sem = asyncio.Semaphore(limit)

    async def _bounded(item):
        async with sem:
            return await fetch_coro(item)

    return list(await asyncio.gather(*(_bounded(item) for item in items)))
