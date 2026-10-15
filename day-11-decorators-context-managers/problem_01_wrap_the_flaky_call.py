"""Problem 1 — @retry: turn "fail once, die" into "try again, then die"
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
An extract job calls a vendor API. At 2 AM the API answers one request
with a 504 — a single timeout — and the whole job dies, because the
call was written as "fail once, die":

    rows = call_api(batch_id)   # one 504 here and the run is over

The fix is a retry loop. Written inline it spreads try/except litter
across every stage; written as a DECORATOR it becomes one line that
changes the call's behavior from the outside:

    @retry(max_attempts=3)
    def call_api(batch_id): ...

Plain words: the decorator is gift wrap — same box (function), new
behavior on the outside (it tries three times before giving up).

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``functools.wraps`` is not decoration: without it the wrapper
    steals ``__name__`` and ``__doc__``, and your logs, metrics, and
    Sentry traces all report the stage as ``"wrapper"``.
  - Only the EXPECTED exceptions are retryable. A ``ValueError`` from
    bad input must propagate on attempt one — retrying a bug is how a
    2 AM timeout becomes a 6 AM billing incident. ``KeyboardInterrupt``
    is a ``BaseException`` and must NEVER be swallowed.
  - After the last attempt, re-raise the LAST exception — not a fresh
    generic one. The original traceback is the evidence.
  - ``max_attempts=1`` must mean exactly one attempt, no retry.

Your solution: ``retry(max_attempts=3, exceptions=(Exception,))`` — a
decorator FACTORY (a function that returns the decorator). Then run
the tests: ``python -m pytest tests -q`` from the day-11 folder.

ANALOGY
-------
Gift wrap: same box, new behavior outside. The function doesn't know
it's retryable — the wrap decides how many knocks before leaving.
"""

from functools import wraps


def retry(max_attempts=3, exceptions=(Exception,)):
    """Retry a function up to ``max_attempts`` times on ``exceptions``.

    Only ``exceptions`` are retried — anything else (including
    ``KeyboardInterrupt``) propagates on the first failure. The last
    exception is re-raised unchanged when attempts run out.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for _ in range(max_attempts - 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    continue
            # Final attempt: no catch — success returns, failure raises
            # the ORIGINAL exception with its traceback intact.
            return fn(*args, **kwargs)

        return wrapper

    return decorator


class ApiTimeout(Exception):
    """Stand-in for a flaky vendor API's timeout error."""


if __name__ == "__main__":
    calls = []

    @retry(max_attempts=3, exceptions=(ApiTimeout,))
    def flaky(n):
        """Fetches batch n from the vendor API."""
        calls.append(n)
        if len(calls) < 3:
            raise ApiTimeout("504 from vendor")
        return ["row1", "row2"]

    print(flaky(7))            # succeeds on attempt 3
    print(flaky.__name__)      # "flaky" — wraps preserved the name
    print(flaky.__doc__.strip())  # original docstring survives
