"""Problem 5 — The 500M users that wouldn't fit
==============================================

THE PROBLEM (beginner foothold first)
------------------------------------
You must count unique users from 500M events a day — but a set of
500M IDs won't fit in memory. Exactness is unaffordable; a tiny,
bounded error is fine.

Write a ``BloomFilter`` class with ``add(item)`` and
``item in bloom`` that answers "seen this?" using a FIXED amount of
memory no matter how many items you add.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A Bloom filter is a bit array with ``k`` hash functions: adding an
item sets ``k`` bits; a lookup checks them. It can NEVER say "no" to
something it saw (no false negatives) but may say "yes" to something
it didn't (false positives) — the price of bounded memory.

Your constructor takes ``capacity`` (expected items) and
``error_rate`` (target false-positive probability) and must size the
bit array and hash count from the optimal formulas:

    m = -(n * ln(p)) / (ln(2)^2)      # bits
    k = (m / n) * ln(2)               # hash functions

Use double hashing (two SHA-256 digests, ``h1 + i*h2``) so ``k``
hashes cost two digest computations. The bytearray must stay the
same size whether you add ten items or ten million — that fixed
size IS the point.

Plain words: a bouncer with a blurry guest list. He never turns away
a real guest, but now and then he waves in a stranger — and his list
fits on an index card no matter how long the line gets.

ANALOGY
-------
A nightclub stamp: the bouncer can't remember 500M faces, so he
stamps wrists with invisible ink and checks stamps under UV light.
He never rejects a stamped guest; occasionally an unstamped wrist
looks stamped under the light — and his memory stays one stamp pad.
"""

from __future__ import annotations

import hashlib
import math


class BloomFilter:
    """Probabilistic set-membership with fixed memory.

    No false negatives; false positives bounded by ``error_rate``
    when at most ``capacity`` items are added.
    """

    def __init__(self, capacity: int, error_rate: float = 0.01):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not 0.0 < error_rate < 1.0:
            raise ValueError("error_rate must be between 0 and 1")
        # Optimal bit-array size and hash count.
        bits = -(capacity * math.log(error_rate)) / (math.log(2) ** 2)
        self.size = int(math.ceil(bits))
        hashes = (self.size / capacity) * math.log(2)
        self.num_hashes = max(1, int(round(hashes)))
        self.bits = bytearray((self.size + 7) // 8)
        self.items_added = 0

    def _positions(self, item):
        data = repr(item).encode("utf-8")
        h1 = int.from_bytes(hashlib.sha256(b"\x00" + data).digest()[:8], "big")
        h2 = int.from_bytes(hashlib.sha256(b"\x01" + data).digest()[:8], "big")
        for i in range(self.num_hashes):
            yield (h1 + i * h2) % self.size

    def add(self, item) -> None:
        for pos in self._positions(item):
            self.bits[pos // 8] |= 1 << (pos % 8)
        self.items_added += 1

    def __contains__(self, item) -> bool:
        return all(
            self.bits[pos // 8] & (1 << (pos % 8))
            for pos in self._positions(item)
        )


if __name__ == "__main__":
    bloom = BloomFilter(capacity=100_000, error_rate=0.01)
    for i in range(100_000):
        bloom.add(f"user-{i}")
    misses = sum(1 for i in range(100_000) if f"user-{i}" not in bloom)
    false_hits = sum(1 for i in range(100_000, 200_000) if f"user-{i}" in bloom)
    print(f"filter bytes: {len(bloom.bits):,}")
    print(f"false negatives: {misses} (must be 0)")
    print(f"false positive rate: {false_hits / 100_000:.4f} (target ~0.01)")
