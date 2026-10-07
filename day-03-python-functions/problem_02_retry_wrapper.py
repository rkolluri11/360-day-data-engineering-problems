"""Problem 2 — The retry wrapper that ate the arguments
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You write a decorator to log calls:

    def log_calls(fn):
        def wrapper(*args, **kwargs):
            print("calling", fn.__name__)
            return fn(*args, **kwargs)
        return wrapper

It works — until someone checks ``fetch_orders.__name__`` in a
dashboard and gets ``"wrapper"``, or the docs generator shows an
empty signature. The wrapper ate the function's identity.

Plain words: a costume that hides the name tag. ``functools.wraps``
puts the tag back on.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your pipeline calls a flaky vendor API. You need
``@retry(times=3, backoff=2.0, exceptions=(TransientError,))`` —
a decorator *factory* (a function returning a decorator) that:

  1. retries ONLY the listed exceptions — a ``ValueError`` from bad
     input must propagate immediately, never be retried;
  2. forwards ``*args``/``**kwargs`` untouched on every attempt;
  3. injects a 1-based ``attempt`` keyword into each call, so the
     function knows which try this is (for logging/backoff headers);
  4. sleeps ``backoff * 2**(attempt-1)`` between attempts
     (exponential backoff), using an injectable sleep function so
     tests never actually wait;
  5. after the last attempt, raises the LAST exception (not a
     wrapper), with the original traceback intact;
  6. preserves ``__name__``, ``__doc__`` and the signature via
     ``functools.wraps`` — dashboards and docs keep working.

The 2 AM version of this bug: the retry wrapper catches
``Exception``, so a programming bug (``KeyError`` from a bad column
name) gets retried 3 times with backoff, turning a 1-second failure
into a 30-second mystery — and the injected ``attempt`` kwarg lands
in a function that never declared it, raising ``TypeError`` on the
*first* try, which then gets "retried" twice more.

Plain words: a good bouncer only turns away the troublemakers on
the list, lets everyone else through untouched, stamps each
re-entry with its number, and never pretends to be the guest.

ANALOGY
-------
A hotel wake-up call service: it redials only when the line was
busy (not when you gave a wrong number), passes your message
word-for-word each time, says "this is attempt 2" so you know,
waits longer between redials — and after the last try, reports
the real busy signal instead of inventing its own story.
"""

from __future__ import annotations

import functools
import time


class TransientError(Exception):
    """Stands in for timeouts, 429s, 503s — worth retrying."""


def retry(times=3, backoff=1.0, exceptions=(Exception,), sleep=time.sleep):
    """Decorator factory: retry the call on listed exceptions.

    Each attempt calls ``fn(*args, **kwargs, attempt=N)`` with N
    starting at 1. Between attempts, sleeps
    ``backoff * 2**(N-1)`` via ``sleep`` (inject a fake in tests).
    Unlisted exceptions propagate immediately. ``functools.wraps``
    keeps the original name, docstring and signature.
    """
    if times < 1:
        raise ValueError("times must be >= 1")

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs, attempt=attempt)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < times:
                        sleep(backoff * 2 ** (attempt - 1))
            raise last_exc

        return wrapper

    return decorator


# --- Example -------------------------------------------------------------

@retry(times=3, backoff=0.0, exceptions=(TransientError,))
def fetch_orders(page, *, attempt=1):
    """Fetch one page of orders; the vendor API flakes."""
    print(f"  attempt {attempt}: fetching page {page}")
    if attempt < 3:
        raise TransientError("vendor 503")
    return [{"page": page, "orders": 42}]


if __name__ == "__main__":
    print(fetch_orders(7))
    print("name preserved:", fetch_orders.__name__)
