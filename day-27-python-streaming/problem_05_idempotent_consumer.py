"""Problem 5 — at-least-once delivery, exactly-once effect.

THE PROBLEM (beginner foothold first)
------------------------------------
Streams redeliver. A consumer that crashes after processing a record
but before committing its offset will see that record again on
restart — and a naive consumer will charge the customer twice, count
the event twice, or insert the row twice.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Every record carries a dedup key (producer id + sequence, or an
    idempotency key). A key seen before is a duplicate: it is never
    processed twice, no matter how often it is redelivered.
  - Committed offsets advance per partition, but only over records
    actually processed or recognised as duplicates — a gap (an offset
    beyond the next expected one) raises instead of silently
    skipping data.
  - Processing is all-or-nothing per record: if the handler raises,
    the key is NOT marked seen and the offset does NOT advance, so
    the record is retried instead of lost.
  - A batch API reports how many records were genuinely new, so a
    pipeline can prove "100 delivered, 97 new, 3 redeliveries" rather
    than guessing.

Plain words: delivery may repeat, but the effect must not — dedup on
the key, commit only what you processed, and never mark a failure
as done.
"""

class GapError(ValueError):
    """Raised when a record's offset skips ahead of the next expected."""


class IdempotentConsumer:
    """Deduping consumer with per-partition committed offsets."""

    def __init__(self):
        self._seen = set()
        self._processed = []
        self._next_offset = {}

    @property
    def processed(self):
        return list(self._processed)

    def committed_offset(self, partition):
        """Next offset to read for ``partition`` (0 if untouched)."""
        return self._next_offset.get(partition, 0)

    def consume(self, partition, offset, dedup_key, value, handler=None):
        """Consume one record; return True if it was genuinely new.

        A redelivered key returns False without reprocessing. A gap
        raises ``GapError``. A handler failure leaves no trace: the
        key stays unseen and the offset uncommitted.
        """
        expected = self._next_offset.get(partition, 0)
        if offset > expected:
            raise GapError(
                f"partition {partition}: offset {offset} skips expected {expected}"
            )
        if dedup_key in self._seen:
            return False
        result = handler(value) if handler is not None else value
        self._seen.add(dedup_key)
        self._processed.append(result)
        self._next_offset[partition] = max(expected, offset + 1)
        return True

    def consume_batch(self, records, handler=None):
        """Consume an iterable of ``(partition, offset, key, value)``.

        Returns the count of genuinely new records. Stops at the
        first gap or handler failure, leaving later records untouched.
        """
        new_count = 0
        for partition, offset, key, value in records:
            if self.consume(partition, offset, key, value, handler=handler):
                new_count += 1
        return new_count
