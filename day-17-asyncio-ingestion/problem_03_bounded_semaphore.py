"""Problem 3 — semaphore: bound the fan-out
============================================

THE PROBLEM (beginner foothold first)
------------------------------------
``asyncio.gather`` over 100,000 urls starts 100,000 connections
at once. The API rate-limits you, the OS runs out of sockets,
or you become your own outage. The fix is a SEMAPHORE — a
counter that only lets N coroutines hold it at a time:

    sem = asyncio.Semaphore(50)

    async def bounded(url):
        async with sem:          # at most 50 inside this block
            return await fetch(url)

    pages = await asyncio.gather(*(bounded(u) for u in urls))

Same fan-out, civilized arrival rate.

Plain words: the semaphore is the bouncer with a clicker — the
club holds 50, the queue outside can be 100,000 long.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Size the semaphore to what the SOURCE tolerates, not what
    your machine can hold. Your box can keep 10,000 sockets
    open; the vendor's WAF will ban your key at 500. Start at
    50 and raise it against the vendor's documented limits.
  - A semaphore does not smooth BURSTS at the start: the first
    50 all fire in the same millisecond. If the API bills per
    second, add a small stagger or a token-bucket rate limiter
    on top.
  - Never share one ``aiohttp.ClientSession`` across threads —
    one session per loop, one loop per thread. Sharing it
    across a thread pool corrupts the connection pool.
  - Hold the semaphore for the WHOLE request (connect +
    download + parse of the response body), not just the
    connect — otherwise 50 connections hold 200 downloads.

Your solution: ``bounded_gather`` below is already written. The
tests track peak concurrency with a shared counter and prove the
cap holds — deterministically, with events, no timers.

ANALOGY
-------
The semaphore is the elevator's max-occupancy sign. The building
has 100,000 visitors today; the elevator still takes 50 at a
time, and nobody pretends the sign is optional.
"""
import asyncio


async def bounded_gather(fetch, urls, limit):
    """Await fetch(url) for every url, at most `limit` in flight at once.

    Results match url order (gather guarantee). Fail-fast: the
    first exception propagates — see problem 5 for the quarantine
    variant.
    """
    sem = asyncio.Semaphore(limit)

    async def _bounded(url):
        async with sem:
            return await fetch(url)

    return list(await asyncio.gather(*(_bounded(u) for u in urls)))
