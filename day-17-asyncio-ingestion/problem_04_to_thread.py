"""Problem 4 — to_thread: never block the loop
==============================================

THE PROBLEM (beginner foothold first)
------------------------------------
The event loop is ONE thread. A coroutine that calls blocking
code — ``time.sleep()``, ``requests.get()``, a heavy parse —
freezes the loop for EVERYONE until it returns. All 1,000 of
your in-flight fetches stop dead.

The escape hatch is ``asyncio.to_thread``: it runs the blocking
function in a worker thread and gives you back an awaitable,
so the loop stays free:

    # WRONG: freezes all 1,000 tasks for the whole parse
    parsed = blocking_parse(blob)

    # RIGHT: parse runs in a thread, loop keeps scheduling
    parsed = await asyncio.to_thread(blocking_parse, blob)

Plain words: to_thread is the sous-chef — the head chef
(the loop) keeps the rail moving while someone else chops.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``to_thread`` is for blocking I/O and LIGHT CPU. A truly
    CPU-heavy parse still burns a thread per call and the GIL
    still serializes it — for heavy compute use
    ``loop.run_in_executor`` with a ProcessPoolExecutor
    (Day 16's model decision, applied inside async code).
  - Exceptions from the threaded function propagate to the
    awaiting coroutine normally — but the traceback crosses
    threads, so log the inputs alongside the error.
  - The default thread pool is capped (min(32, cpu+4)
    workers). 10,000 concurrent ``to_thread`` calls queue up —
    wrap it in the Day-17 semaphore too, or pass your own
    ``ThreadPoolExecutor(max_workers=...)`` via
    ``run_in_executor``.
  - Blocking calls HIDE inside innocent-looking helpers:
    a "parse" that logs to a synchronous DB driver, a
    "validate" that hits disk. Audit the call tree, not just
    the top frame.

Your solution: ``process_async`` (to_thread) and
``process_naive`` (the trap) are already written. The tests log
the exact event order — a looper coroutine ticking while the
parse is gated — and prove only one version keeps the loop
alive. No timing bets: the assertions are about log order.

ANALOGY
-------
The loop is a DJ with one turntable. to_thread is handing the
mic to a guest singer — the music never stops. Calling blocking
code directly is the DJ taking a phone call mid-set.
"""
import asyncio


def parse_blocking(blob, release, log):
    """A blocking parse: logs start, waits on a thread gate, logs end.

    `release` is a threading.Event the test controls; the wait
    models a slow synchronous call (disk, legacy driver, sleep).
    Whatever thread calls this BLOCKS until release is set.
    """
    log.append(("parse_start", blob))
    release.wait()  # blocks THIS thread — the whole point of the demo
    log.append(("parse_end", blob))
    return blob.upper()


async def process_async(blobs, log, release):
    """Parse every blob in worker threads; the loop stays free."""
    return list(
        await asyncio.gather(
            *(asyncio.to_thread(parse_blocking, b, release, log) for b in blobs)
        )
    )


async def process_naive(blobs, log, release):
    """THE TRAP: blocking parse called directly — freezes the whole loop."""
    return [parse_blocking(b, release, log) for b in blobs]
