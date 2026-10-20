"""Problem 5 — backpressure traps: timeouts, errors, and the quarantine
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A production fan-out needs three guards gather alone does not
give you:

  1. BOUND it — ``asyncio.Semaphore`` (problem 3), so you never
     open 100,000 connections at once.
  2. TIME it out — ``asyncio.wait_for(fetch(u), timeout)``, so
     one hung API cannot pin your pipeline forever.
  3. QUARANTINE failures — ``gather(..., return_exceptions=True)``,
     so one bad page becomes a routed record, not a crashed
     batch (the Day 15 instinct, applied to async).

``safe_gather`` below composes all three and returns one record
per url: ``(url, status, value)`` where status is "ok",
"timeout", or "error".

Plain words: bound is the bouncer, timeout is the last train
home, quarantine is secondary screening — the flight still
boards.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``wait_for`` CANCELS the timed-out coroutine. If your fetch
    holds a connection or a lock, cancellation must release it
    — write fetches with ``try/finally`` or
    ``async with`` so a timeout cannot leak resources.
  - With ``return_exceptions=True``, ``asyncio.CancelledError``
    is still special: in Python 3.8+ it is NOT swallowed into
    the results list, it propagates. Catch it explicitly when
    you shut a fan-out down on purpose.
  - A timeout on the WHOLE gather is not the same as a timeout
    per item: the former aborts the batch, the latter routes
    the slow ones and keeps the batch. Choose per item.
  - Retries belong OUTSIDE this function, with backoff and a
    retry budget — retrying inside the fan-out without a cap
    turns one slow API into an infinite self-DDoS.

Your solution: ``safe_gather`` is already written. The tests
script one ok url, one slow url, and one raising url with
events, and prove each guard fires independently.

ANALOGY
-------
safe_gather is airport security at scale: the bouncer caps the
line (semaphore), anyone standing too long gets waved through
to a side room (timeout), and a flagged bag never grounds the
flight (quarantine).
"""
import asyncio


async def safe_gather(fetch, urls, limit, timeout):
    """Bounded, per-item-timeout fan-out with per-url quarantine.

    Returns [(url, status, value), ...] in url order, where status
    is "ok" (value = fetch result), "timeout" (value = the
    TimeoutError), or "error" (value = the raised exception).
    """
    sem = asyncio.Semaphore(limit)

    async def _guarded(url):
        async with sem:
            try:
                value = await asyncio.wait_for(fetch(url), timeout)
            except asyncio.TimeoutError as exc:
                return (url, "timeout", exc)
            except Exception as exc:  # noqa: BLE001 — quarantine by design
                return (url, "error", exc)
            return (url, "ok", value)

    return list(await asyncio.gather(*(_guarded(u) for u in urls)))
