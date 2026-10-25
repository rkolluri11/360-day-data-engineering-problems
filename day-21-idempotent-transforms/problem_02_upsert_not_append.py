"""Problem 2 — upsert, don't append: the store absorbs replays
============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A batch lands twice — a retry, a redelivered file, a rerun
after a crash. Appending the batch doubles every row:

    # NOT idempotent: replay doubles the table
    rows.extend(batch)            # 100 rows -> 200 rows

Upserting by a stable key absorbs the replay: the same key
overwrites the same slot with the same value:

    # idempotent: replay changes nothing
    for key, record in batch:
        store[key] = record       # 100 rows -> 100 rows

The key is the whole trick. No key, no idempotency: a bare
list cannot tell a replay from a genuinely new row.

Plain words: appending is pouring water into a bucket — a
second pour overflows it. Upserting is putting a labelled box
on a shelf — putting the same box there twice leaves one box.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The key must be STABLE across retries: a UUID generated at
    insert time makes every retry look new. Derive the key from
    the business identity (order_id, event_id), never from the
    attempt.
  - Upsert is last-write-wins. A replay carrying the SAME value
    is harmless; a replay carrying a STALE value after a newer
    correction silently reverts it. When corrections exist, the
    writer must carry a version or timestamp and refuse to go
    backwards (see Problem 5's processed-set pattern for the
    stronger variant).
  - Store a COPY of the record, not the caller's dict. Aliasing
    lets the caller mutate a "committed" row after the fact —
    the store then changes without any write happening.
  - ``apply_batch`` must be atomic in intent: replaying the
    whole batch, not just one row, leaves the store identical.

Your solution: ``upsert`` and ``apply_batch`` are already
written. The tests prove a full-batch replay is a no-op, and
that a genuine update still lands.

ANALOGY
-------
Upsert is saving a file under the same name. Save it twice and
you have one file. Appending is printing it twice and filing
both copies.
"""

import copy


def upsert(store, key, record):
    """Write record under key, overwriting any previous value."""
    store[key] = copy.deepcopy(record)
    return store[key]


def apply_batch(store, batch):
    """Apply an iterable of (key, record) pairs via upsert.

    Returns the store. Replaying the identical batch afterwards
    leaves the store exactly as it was.
    """
    for key, record in batch:
        upsert(store, key, record)
    return store
