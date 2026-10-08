"""Problem 9 — The error list that remembered yesterday
===================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A helper collects bad row ids into a list:

    def collect(row, bad=[]):       # <- the trap is right here
        if row["status"] == "bad":
            bad.append(row["id"])
        return bad

Call it twice and the second call sees the first call's ids. The
default list ``[]`` is created *once* — when the function is defined
— and every call without an explicit list shares that same object.

Plain words: the function was given one shared notebook at birth,
and every caller writes in the same notebook forever.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The validation step quarantines bad rows per batch and emails the
count: ``quarantine(batch_rows)``. After a refactor it uses a
mutable default accumulator. Batch 1 has 3 bad rows; batch 2 is
perfectly clean — but its report says "3 quarantined". The data
quality alert fires, the on-call spends an hour hunting phantom
errors, and after three false alarms the team starts ignoring the
alert that will one day be real.

The dict variant is sneakier: ``def enrich(row, ctx={})`` mutates
``ctx`` in place, so enrichment context from one tenant's rows
bleeds into the next tenant's — a cross-tenant data leak wearing a
default argument as a disguise.

Your solution: ``collect_errors`` uses the ``errors=None`` idiom —
a fresh list per call unless the caller passes one in explicitly.
``merge_context`` never mutates its inputs; it returns a new dict.

Plain words: hand every meeting a fresh whiteboard. If someone
brings their own board, write on theirs — but never scribble on
yesterday's.

ANALOGY
-------
A meeting-room whiteboard that is never erased: Tuesday's notes are
still there on Wednesday, and Wednesday's decisions get blamed for
Tuesday's mistakes. Fresh board per meeting, or bring your own.
"""

from __future__ import annotations


def collect_errors_buggy(row, errors=[]):
    """DO NOT USE — demonstrates the trap.

    The default ``[]`` is created once at function-definition time,
    so every call shares it and errors leak across batches.
    """
    if row.get("status") == "bad":
        errors.append(row["id"])
    return errors


def collect_errors(row, errors=None):
    """Collect a bad row id; each call gets a FRESH list by default.

    Pass an explicit list to accumulate across rows within one batch;
    omit it and yesterday's batch can never pollute today's.
    """
    if errors is None:
        errors = []                      # fresh whiteboard per call
    if row.get("status") == "bad":
        errors.append(row["id"])
    return errors


def merge_context(base, extra=None):
    """Return a NEW dict combining base and extra; inputs untouched.

    The ``extra=None`` idiom plus ``{**base, **extra}`` means no
    caller can ever mutate a shared default dict by accident.
    """
    if extra is None:
        extra = {}
    return {**base, **extra}              # new dict; base and extra survive


if __name__ == "__main__":
    # --- The trap, live ------------------------------------------------
    b1 = [{"id": 1, "status": "bad"}, {"id": 2, "status": "ok"}]
    b2 = [{"id": 3, "status": "ok"}]

    for row in b1:
        collect_errors_buggy(row)
    print("buggy, batch 2 sees:", collect_errors_buggy(b2[0]),
          "<- batch 1's ghost")

    # --- The fix --------------------------------------------------------
    acc = []
    for row in b1:
        acc = collect_errors(row, acc)   # explicit accumulator: intended sharing
    print("fixed, batch 1:", acc)
    print("fixed, batch 2:", collect_errors(b2[0]), "<- clean slate")

    # --- Dict variant ----------------------------------------------------
    tenant_a = {"region": "us"}
    view = merge_context(tenant_a, {"plan": "pro"})
    print("merged:", view, "| original untouched:", tenant_a)
