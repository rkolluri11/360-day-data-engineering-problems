"""Problem 4 — retry the transient, bury the permanent.

THE PROBLEM (beginner foothold first)
------------------------------------
A send fails. Sometimes the broker was briefly unreachable and a
retry a second later succeeds; sometimes the record itself is bad
and retrying it a thousand times will never help. Treating both the
same way either loses good data or poisons the pipeline with an
endless retry loop.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Errors are classified at the raise site: ``TransientError``
    (worth retrying) vs ``PermanentError`` (never worth retrying).
    Anything else propagates — the retry loop must not swallow bugs.
  - Backoff is exponential and capped: delay doubles each retry up
    to ``max_delay_ms``, so a sick broker is not hammered at full
    rate while it recovers.
  - Retries are bounded: after ``max_attempts`` attempts a transient
    failure is declared dead and the record goes to the dead-letter
    queue (DLQ) with its error and attempt count — nothing vanishes.
  - A permanent failure goes straight to the DLQ on attempt 1; it
    never burns the retry budget.

Plain words: retry what time can fix, dead-letter what it can't, and
keep the receipt for both.
"""

from collections import namedtuple

DeliveryResult = namedtuple("DeliveryResult", ["success", "attempts", "delays_ms"])


class DeliveryError(Exception):
    """Base class for classified delivery failures."""


class TransientError(DeliveryError):
    """A failure worth retrying (broker hiccup, timeout, throttle)."""


class PermanentError(DeliveryError):
    """A failure retrying cannot fix (bad record, auth, unknown topic)."""


class RetryPolicy:
    """Bounded exponential backoff, capped at ``max_delay_ms``."""

    def __init__(self, max_attempts=3, base_delay_ms=100, factor=2, max_delay_ms=10000):
        if max_attempts < 1 or base_delay_ms < 0 or factor < 1 or max_delay_ms < base_delay_ms:
            raise ValueError("invalid retry policy parameters")
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.factor = factor
        self.max_delay_ms = max_delay_ms

    def delay_for(self, retry_number):
        """Delay in ms before retry ``retry_number`` (1 = first retry)."""
        if retry_number < 1:
            raise ValueError("retry_number must be >= 1")
        delay = self.base_delay_ms * (self.factor ** (retry_number - 1))
        return min(delay, self.max_delay_ms)


class DeadLetterQueue:
    """The receipt drawer: every record that could not be delivered."""

    def __init__(self):
        self.entries = []

    def add(self, record, error, attempts):
        self.entries.append({"record": record, "error": str(error), "attempts": attempts})

    def __len__(self):
        return len(self.entries)


def deliver(send, record, policy, dlq=None):
    """Deliver ``record`` via ``send`` under ``policy``.

    Returns a ``DeliveryResult``. No sleeping happens here — the
    delays that *would* be waited are reported, so callers (and
    tests) stay deterministic. Unclassified exceptions propagate.
    """
    delays = []
    for attempt in range(1, policy.max_attempts + 1):
        try:
            send(record)
            return DeliveryResult(True, attempt, delays)
        except PermanentError as exc:
            if dlq is not None:
                dlq.add(record, exc, attempt)
            return DeliveryResult(False, attempt, delays)
        except TransientError as exc:
            if attempt >= policy.max_attempts:
                if dlq is not None:
                    dlq.add(record, exc, attempt)
                return DeliveryResult(False, attempt, delays)
            delays.append(policy.delay_for(attempt))
    return DeliveryResult(False, policy.max_attempts, delays)
