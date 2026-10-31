"""Problem 3 — send in batches, or pay per record forever.

THE PROBLEM (beginner foothold first)
------------------------------------
Sending one network request per event is simple and ruinously slow:
every record pays the full cost of a round trip. Batching amortises
that cost — but an unbounded batch is a memory bomb, and a batch that
waits forever for "just one more record" is a latency bomb.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A batch is bounded twice: by record count AND by total bytes.
    Whichever limit is hit first flushes the batch.
  - A single record larger than the byte limit is rejected outright —
    it could never fit in any batch, so queuing it would stall the
    producer forever.
  - Flushing is explicit too: ``flush()`` returns whatever is
    pending, even a partial batch, and leaves the producer empty.
  - A linger bound caps waiting: a batch is "ready" once it has aged
    past ``linger_ms``, even if it is not full. The clock is
    injectable, so readiness is testable without sleeping.

Plain words: batch for throughput, bound it twice, and never let a
batch wait longer than the linger you promised.
"""

import time


class BatchError(ValueError):
    """Raised for an oversize record or an invalid batcher config."""


def _size_of(value):
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    raise BatchError("record value must be str or bytes")


class Batcher:
    """Count- and byte-bounded batching with a linger bound."""

    def __init__(self, max_records=100, max_bytes=65536, linger_ms=0, clock=None):
        if max_records < 1 or max_bytes < 1 or linger_ms < 0:
            raise BatchError("max_records/max_bytes must be >= 1, linger_ms >= 0")
        self.max_records = max_records
        self.max_bytes = max_bytes
        self.linger_ms = linger_ms
        self._clock = clock or time.monotonic
        self._pending = []
        self._pending_bytes = 0
        self._started_at = None

    @property
    def pending_count(self):
        return len(self._pending)

    @property
    def pending_bytes(self):
        return self._pending_bytes

    def add(self, value):
        """Add ``value``; return the flushed batch if a limit was hit.

        When the new record would overflow the pending batch, the
        pending batch is flushed first and the record starts a fresh
        batch. Returns ``None`` when nothing flushed.
        """
        size = _size_of(value)
        if size > self.max_bytes:
            raise BatchError(f"record of {size} bytes exceeds max_bytes {self.max_bytes}")
        flushed = None
        if self._pending and (
            len(self._pending) + 1 > self.max_records
            or self._pending_bytes + size > self.max_bytes
        ):
            flushed = self.flush()
        if not self._pending:
            self._started_at = self._clock()
        self._pending.append(value)
        self._pending_bytes += size
        return flushed

    def is_ready(self):
        """True when a pending batch has aged past ``linger_ms``."""
        if not self._pending or self._started_at is None:
            return False
        elapsed_ms = (self._clock() - self._started_at) * 1000
        return elapsed_ms >= self.linger_ms

    def flush(self):
        """Return the pending batch (possibly empty) and reset."""
        batch, self._pending = self._pending, []
        self._pending_bytes = 0
        self._started_at = None
        return batch
