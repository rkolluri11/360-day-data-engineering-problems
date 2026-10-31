"""Problem 1 — the key decides the partition, and the partition decides the order.

THE PROBLEM (beginner foothold first)
------------------------------------
A stream topic is split into partitions, and each partition is an
append-only log: records land in order and are read back in that
order. That order guarantee holds *within one partition only*. Two
records for the same customer that land in different partitions can
be read in either order — so a "balance updated" event can overtake
the "balance created" event it depends on.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A keyed record always lands in the same partition: the partition
    is a stable hash of the key modulo the partition count, so all
    events for one key stay in order, forever, across restarts.
  - An unkeyed record has no ordering promise: it round-robins across
    partitions, spreading load evenly.
  - Offsets are per-partition, start at 0, and increase by exactly 1
    per record — a consumer resumes from its last committed offset
    and never re-reads (or skips) a record by accident.
  - Reading a partition returns records in offset order, from the
    requested offset onward; an out-of-range partition is a caller
    bug, not an empty page.

Plain words: same key, same partition, same order — that is the only
ordering a stream promises, and the key is how you buy it.
"""

import zlib

from itertools import count


class TopicError(ValueError):
    """Raised for an invalid partition count, partition, or key."""


class PartitionedTopic:
    """An in-memory, append-only topic with per-partition offsets."""

    def __init__(self, partition_count):
        if not isinstance(partition_count, int) or partition_count < 1:
            raise TopicError("partition_count must be a positive integer")
        self.partition_count = partition_count
        self._logs = [[] for _ in range(partition_count)]
        self._round_robin = count()

    def partition_for(self, key):
        """Return the partition a record with ``key`` must land in.

        ``None`` (unkeyed) round-robins; any other key hashes stably,
        so the answer never changes between calls or processes.
        """
        if key is None:
            return next(self._round_robin) % self.partition_count
        if not isinstance(key, str):
            raise TopicError("key must be a string or None")
        return zlib.crc32(key.encode("utf-8")) % self.partition_count

    def produce(self, key, value):
        """Append ``value`` and return ``(partition, offset)``."""
        partition = self.partition_for(key)
        log = self._logs[partition]
        offset = len(log)
        log.append((offset, key, value))
        return partition, offset

    def read(self, partition, from_offset=0):
        """Return ``[(offset, key, value), ...]`` in offset order."""
        if not isinstance(partition, int) or not 0 <= partition < self.partition_count:
            raise TopicError(f"unknown partition: {partition!r}")
        if from_offset < 0:
            raise TopicError("from_offset must be >= 0")
        return [entry for entry in self._logs[partition] if entry[0] >= from_offset]

    def partition_size(self, partition):
        """Return how many records a partition holds."""
        if not isinstance(partition, int) or not 0 <= partition < self.partition_count:
            raise TopicError(f"unknown partition: {partition!r}")
        return len(self._logs[partition])
