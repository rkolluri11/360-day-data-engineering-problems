"""Problem 5 — @retry OUTSIDE, with block INSIDE: retry the attempt, never leak
============================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Problems 1–4 each fix one half of the 2 AM story. Production needs
both at once: RETRY the flaky vendor call (Problem 1, with backoff
from Problem 2) while NEVER leaking the connection (Problem 4). The
order is the whole lesson:

    @retry(...)            # OUTSIDE: a failed attempt retries everything
    def extract_batch(id):
        with managed_connection(pool) as conn:   # INSIDE: each attempt
            return call_api(id, conn)            # opens AND closes cleanly

Flip them — retry inside the ``with`` — and one block holds the SAME
connection across all attempts: the failed attempt's broken cursor
gets reused, and a leak compounds across retries.

Plain words: retry wraps the trip, the ``with`` block wraps the truck.
A new truck for every trip; the retry just books another trip.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Each attempt must open AND close its own connection. The pool here
    tracks every connection it hands out, so the tests can count:
    attempts == connections opened == connections closed. ALWAYS.
  - A failed attempt ROLLS BACK (the partial batch is poison) and the
    successful one COMMITS. Retry without rollback is how a partial
    batch lands twice.
  - Only the vendor's timeout is retried. A ``ValueError`` from bad
    input propagates after attempt one — but the connection from that
    attempt still closes.
  - Backoff between attempts uses an injected sleep so the test suite
    doesn't wait for real seconds.

Your solution: ``build_pipeline(failures, pool, sleeps)`` — returns an
``extract_batch`` with retry outside and the ``with`` block inside.
Then run the tests: ``python -m pytest tests -q``.

ANALOGY
-------
The post's line, made concrete: retry is the travel agent rebooking
the trip; the ``with`` block is the truck that comes back with a full
tank every time — even on the trips that get cancelled.
"""

from problem_01_wrap_the_flaky_call import ApiTimeout
from problem_02_backoff_not_hammering import retry_backoff
from problem_04_with_blocks import FakeConnection, managed_connection


class FakePool:
    """Hands out tracked connections so tests can audit the lifecycle."""

    def __init__(self):
        self.connections = []

    def acquire(self):
        conn = FakeConnection()
        self.connections.append(conn)
        return conn


def call_vendor_api(batch_id, conn, failures):
    """Simulated flaky vendor API: raises ApiTimeout while ``failures``
    is non-empty, then 'returns' rows. A bad batch id is a bug, not a
    timeout — it must NOT be retried."""
    if batch_id < 0:
        raise ValueError(f"bad batch id: {batch_id}")
    if failures:
        failures.pop()
        raise ApiTimeout("504 from vendor")
    return [f"row-{batch_id}-a", f"row-{batch_id}-b"]


def build_pipeline(failures, pool, sleeps):
    """Build the production extract: retry (with backoff) OUTSIDE, the
    ``with`` block INSIDE. ``failures`` is a mutable countdown shared
    with the fake API; ``sleeps`` records backoff delays."""

    @retry_backoff(max_attempts=3, base=1.0, exceptions=(ApiTimeout,),
                   sleep=sleeps.append)
    def extract_batch(batch_id):
        with managed_connection(pool.acquire) as conn:
            return call_vendor_api(batch_id, conn, failures)

    return extract_batch


if __name__ == "__main__":
    pool, sleeps = FakePool(), []
    extract = build_pipeline(["f", "f"], pool, sleeps)  # 2 failures, then ok
    print(extract(7))
    print("attempts/connections:", len(pool.connections))
    print("backoffs:", sleeps)
    for i, c in enumerate(pool.connections):
        print(f"conn {i}: committed={c.committed} rolled_back={c.rolled_back} "
              f"closed={c.closed}")
