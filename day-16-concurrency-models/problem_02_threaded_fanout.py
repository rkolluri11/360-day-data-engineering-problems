"""Problem 2 — threaded fan-out: ThreadPoolExecutor for I/O-bound work
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You must call 200 API endpoints. Serially, each call blocks for
300 ms while the network answers — 60 seconds of mostly waiting.
With threads, while one thread blocks on its socket it RELEASES
the GIL, so 32 threads wait in parallel and the batch finishes
in ~2 seconds.

``ThreadPoolExecutor`` is the tool: ``pool.map(fn, items)``
applies ``fn`` to every item across the pool and returns results
in INPUT order, even though threads finish out of order.

Plain words: one waiter taking 200 orders serially vs 32
waiters each taking a table — the kitchen (the API) is the
bottleneck either way, but nobody idles.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - One bad URL must not kill the batch: capture per-item
    exceptions as data — (ok, result-or-error) tuples — instead
    of letting one failure cancel 199 good calls.
  - Results must stay aligned with inputs: index into a
    pre-sized list rather than appending from threads (append
    order is finish order, not input order).
  - ``max_workers`` is a throttle, not a wish: 32 threads
    against a polite API is fan-out; 500 is a self-inflicted
    DDoS. Size it to what the source tolerates.
  - Threads share memory, so the results list is visible to
    every worker — but each thread writes only its OWN slot,
    which is why no lock is needed here.

Your solution: ``fetch_all`` below is already written. Read it,
then run the tests: ``python -m pytest tests -q`` from the
day-16 folder.

ANALOGY
-------
A thread pool is a taxi fleet with a dispatcher: you hand over
200 addresses, the dispatcher assigns cabs, and every passenger
arrives — one flat tire doesn't strand the other 199.
"""

from concurrent.futures import ThreadPoolExecutor


def fetch_all(fetch_one, items, max_workers=8):
    """Call fetch_one(item) for every item on a thread pool.

    Returns a list aligned with `items`: (True, result) on success,
    (False, exception) on failure — one bad item never kills the batch.
    """
    results = [None] * len(items)

    def _run(i, item):
        try:
            results[i] = (True, fetch_one(item))
        except Exception as exc:  # noqa: BLE001 - per-item capture is the point
            results[i] = (False, exc)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_run, i, item) for i, item in enumerate(items)]
        for future in futures:
            future.result()  # raises nothing: _run already captured per-item errors
    return results
