"""Problem 5 — the replay-safe pipeline: all five ideas, end to end
================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A real pipeline is not one trick — it is the whole stack, and
one non-idempotent stage poisons the rest. An order-events
pipeline replays safely only if every stage is replay-safe:

    1. normalize each event (Problem 1: pure, no mutation)
    2. skip events already processed (the processed-set gate)
    3. upsert by order_id (Problem 2: replay overwrites itself)
    4. write the output atomically (Problem 4: never half)

Drop any one and a retry corrupts something: un-normalized
amounts double-round, un-gated events double-count, appended
rows duplicate, torn files mislead the next reader.

Plain words: a replay-safe pipeline is a kitchen that can cook
the same ticket twice without serving two dinners. The ticket
number is checked at the door, the dish replaces itself on the
pass, and the plate is swapped whole.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The processed-set gate must be DURABLE, not in-memory.
    This demo keeps it in a set for clarity; a real pipeline
    stores processed event ids in the same store as the output
    (or the same transaction), or a restart forgets what it
    already did and replays everything as new.
  - Gate BEFORE side effects, not after. Checking "already
    processed" after writing the row is a race: two concurrent
    attempts both pass the check, both write. Gate first, and
    make the gate itself atomic (a unique constraint on the
    event id is the production form of this set).
  - A correction is a NEW event_id for the SAME order_id. The
    gate must key on event_id (so the correction is not skipped
    as a duplicate) while the store keys on order_id (so the
    correction overwrites the old amount instead of adding a
    second row). Confusing the two keys is the classic bug:
    gate on order_id and corrections are dropped; store on
    event_id and corrections double-count.
  - Revenue is computed from the STORE, never from a running
    counter. A counter incremented per event double-counts on
    replay; a sum over the upserted store is stable by
    construction.

Your solution: ``run_pipeline`` and ``total_revenue`` are
already written. The tests prove a full replay is a no-op, a
duplicate event_id inside one batch is processed once, and a
correction updates the amount exactly once.

ANALOGY
-------
The pipeline is a hotel check-in desk with a guest ledger. A
guest who checks in twice gets one room, not two — but a guest
who extends their stay (a new form, same name) updates the one
booking instead of opening a second.
"""

import copy


def run_pipeline(store, processed, events):
    """Apply order events to store, replay-safely.

    ``store`` maps order_id -> {"order_id", "amount"}.
    ``processed`` is a set of event_ids already applied.
    Each event: {"event_id", "order_id", "amount"}.

    Events whose event_id is already in ``processed`` are
    skipped. New events are upserted by order_id and marked
    processed. Returns (store, processed).
    """
    for event in events:
        event_id = event["event_id"]
        if event_id in processed:
            continue
        processed.add(event_id)
        store[event["order_id"]] = {
            "order_id": event["order_id"],
            "amount": round(float(event["amount"]), 2),
        }
    return store, processed


def total_revenue(store):
    """Revenue from the store — never from a running counter."""
    return round(sum(row["amount"] for row in store.values()), 2)


def snapshot(store):
    """Deep-copy helper for tests: freeze a store for comparison."""
    return copy.deepcopy(store)
