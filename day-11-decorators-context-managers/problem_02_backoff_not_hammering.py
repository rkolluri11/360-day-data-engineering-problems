"""Problem 2 — Exponential backoff: retry without hammering the sick API
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Problem 1's retry fires attempt two the INSTANT attempt one fails. Do
that against an API that just fell over and you are not recovering —
you are hammering a sick server with zero recovery time, and rate
limiters will start dropping you for it. Production retries wait
longer each time: 1s, 2s, 4s, ... — EXPONENTIAL BACKOFF.

    attempt 0 fails -> sleep 1s -> attempt 1 fails -> sleep 2s -> ...

Plain words: knock, wait a beat; knock again, wait longer. Don't bang
on the door while the person behind it is getting up.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - An uncapped backoff is a landmine: 2**20 seconds is 12 days. A CAP
    (``min(delay, cap)``) keeps a stuck job from sleeping forever.
  - Synchronized retries are a THUNDERING HERD: fifty workers failing
    at once all wake at second 4 and stampede the API together. JITTER
    (randomizing the delay) spreads the wake-ups. The RNG is injected
    so tests stay deterministic.
  - The sleep is injected too (``sleep`` defaults to ``time.sleep``),
    so tests record the delays instead of actually waiting 7 seconds.

Your solution: ``backoff_delay(attempt, base, cap, jitter, rng)`` and
``retry_backoff(...)`` — a retry decorator that sleeps the backoff
between attempts. Then run the tests: ``python -m pytest tests -q``.

ANALOGY
-------
The retry is the knock; backoff is how long you wait between knocks.
Banging every second gets the door slammed. Waiting longer each time
gives the house time to answer — and jitter keeps the whole street
from knocking at once.
"""

import random
import time
from functools import wraps


def backoff_delay(attempt, base=1.0, cap=60.0, jitter=0.0, rng=None):
    """Delay in seconds before retry number ``attempt`` (0-based).

    Geometric: ``base * 2**attempt``, clipped to ``cap``. When
    ``jitter`` > 0 the delay is multiplied by a random factor in
    ``[1 - jitter, 1]`` — full jitter (``jitter=1.0``) spreads wake-ups
    across ``[0, delay]``.
    """
    delay = min(base * (2 ** attempt), cap)
    if jitter:
        r = rng() if rng is not None else random.random()
        delay *= (1 - jitter) + jitter * r
    return delay


def retry_backoff(max_attempts=3, base=1.0, cap=60.0, jitter=0.0,
                  exceptions=(Exception,), sleep=time.sleep, rng=None):
    """Retry decorator with exponential backoff between attempts.

    ``sleep`` and ``rng`` are injectable so tests can record delays and
    stay deterministic. Only ``exceptions`` are retried; the last
    exception is re-raised after the final attempt.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    if attempt == max_attempts - 1:
                        raise
                    sleep(backoff_delay(attempt, base, cap, jitter, rng))

        return wrapper

    return decorator


if __name__ == "__main__":
    delays = []

    @retry_backoff(max_attempts=4, base=1.0, sleep=delays.append)
    def always_fails():
        raise ConnectionError("sick API")

    try:
        always_fails()
    except ConnectionError:
        pass
    print("sleeps between attempts:", delays)  # [1.0, 2.0, 4.0]
    print("cap demo:", [backoff_delay(a, base=10.0, cap=30.0) for a in range(4)])
    # [10.0, 20.0, 30.0, 30.0]
