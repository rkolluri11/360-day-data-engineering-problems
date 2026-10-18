"""Problem 5 — transient vs permanent: retry only what can recover
==================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Some failures heal with time (timeouts, 429 rate limits, a source that
is briefly down). Some never will (a schema violation, a malformed
record, a revoked credential). Retrying the second kind is burning money
and minutes:

    class TransientError(StageError):
        "Timeouts, 429s, throttling - backoff and retry."

    class PermanentError(PipelineError):
        "Schema violations, bad credentials - zero retries."

The retry policy: ``TransientError`` earns exponential backoff
(1s, 2s, 4s ...); ``PermanentError`` is re-raised immediately. Never
retry garbage — a bad schema will not heal in 60 seconds.

Plain words: transient errors are a traffic jam — waiting works.
Permanent errors are a dead end — waiting is just idling.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Exponential backoff: ``delay = min(cap, base * 2 ** attempt)``.
    The cap stops one wedged dependency from sleeping your pipeline for
    an hour; jitter (not shown here) stops 200 workers retrying in
    lockstep — the thundering herd.
  - The sleeper is injectable (``sleep=``): tests record the delays
    instead of actually sleeping, so the suite stays fast and
    deterministic.
  - Attempt counting starts at 0: the first retry waits ``base``.
  - ``parse_amount`` is the end-to-end demo: non-numeric strings raise
    ``PermanentError`` (no retry, quarantine immediately), while a
    flaky source raises ``TransientError`` a scripted number of times —
    the stage recovers without a human.
  - Anything that is NOT a known error type is re-raised untouched:
    the taxonomy routes its own; it never masks strangers.

Your solution: ``backoff_delay``, ``run_with_retry`` and
``parse_amount`` below. Then run the tests: ``python -m pytest tests
-q`` from the day-15 folder.

ANALOGY
-------
Backoff is a polite knock. First knock soft, then louder, then you
leave — you do not hammer the door for an hour when the house is
clearly empty.
"""

import time

from problem_01_base_error import PipelineError, RowError, StageError


class TransientError(StageError):
    """Timeouts, 429s, throttling — backoff and retry."""


class PermanentError(PipelineError):
    """Schema violations, bad credentials — zero retries, route now."""


def backoff_delay(attempt, base=1.0, cap=60.0):
    """Exponential backoff for retry attempt number `attempt` (0-based)."""
    return min(cap, base * (2 ** attempt))


def run_with_retry(fn, max_attempts=4, base=1.0, cap=60.0, sleep=time.sleep):
    """Run fn(), retrying only TransientError with exponential backoff.

    PermanentError and unknown exceptions are re-raised immediately —
    garbage is never retried. Returns (result, attempts_used).
    """
    attempt = 0
    while True:
        try:
            return fn(), attempt + 1
        except TransientError:
            if attempt + 1 >= max_attempts:
                raise
            sleep(backoff_delay(attempt, base=base, cap=cap))
            attempt += 1


def parse_amount(raw):
    """Parse a money string; non-numeric input is permanent, not transient."""
    if raw is None:
        return None
    cleaned = str(raw).strip().replace(",", "").replace("$", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError:
        raise PermanentError(f"bad amount {raw!r}: not numeric")


class FlakySource:
    """A scripted source that fails transiently `fail_times` times, then works."""

    def __init__(self, payload, fail_times=2):
        self.payload = payload
        self.fail_times = fail_times
        self.calls = 0

    def fetch(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TransientError(f"source busy (call {self.calls})")
        return self.payload
