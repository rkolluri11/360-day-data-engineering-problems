"""Problem 1 — the pure replay: f(f(x)) must equal f(x)
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline retries. A step runs, the worker dies before it can
say "done", the orchestrator runs the step again. If the step
APPENDS, the retry duplicates the data:

    # NOT idempotent: run it twice, get it twice
    out.append(clean(row))        # retry -> two copies

If the step ASSIGNS a cleaned value to a fixed key, the retry
overwrites with the identical value:

    # idempotent: run it twice, get it once
    out[row["id"]] = clean(row)   # retry -> same row, once

``normalize_event`` is the pure version of that idea: a function
of its input only, no hidden state, no mutation, no append. Run
it once or five times and the answer is the same.

Plain words: a pure transform is a stamp, not a tally counter.
Stamping the same letter twice leaves one stamp. Counting it
twice leaves two.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Purity is not enough on its own: ``normalize`` must also
    not mutate its input. A function that strips a dict IN PLACE
    is idempotent on its own output but corrupts the caller's
    copy — and the retry then reads already-cleaned data as if
    it were raw. Copy first, then clean.
  - Sorting + deduping a list is idempotent; appending to it is
    not. Any step whose output feeds its own next input must be
    checked for f(f(x)) == f(x), not just f(x) == expected.
  - Rounding matters: ``round(19.999, 2)`` is 20.0, and rounding
    20.0 again is still 20.0 — a fixed point. A transform with
    no fixed point (say, "add 10%") can never be replay-safe.
  - Normalization must be TOTAL: every field it touches reaches
    a canonical form (stripped, lowercased, rounded, sorted),
    or the second run finds a leftover un-normalized corner
    and changes the answer.

Your solution: ``normalize_event`` is already written. The
tests prove the replay law — normalize(normalize(e)) equals
normalize(e) — plus no-mutation and determinism.

ANALOGY
-------
Normalizing an event is ironing a shirt. Iron it once, it is
flat. Iron it again, it is still flat — not flatter, not torn.
Appending is stacking chairs: do it twice and you have two
stacks.
"""

import copy


def normalize_event(event):
    """Return a canonical copy of an event dict. Never mutates input.

    Canonical form: user_id stripped; email stripped and lowercased;
    amount coerced to a float rounded to 2 decimals; tags sorted
    with duplicates removed. Missing fields pass through untouched.
    """
    out = copy.deepcopy(event)
    if "user_id" in out and isinstance(out["user_id"], str):
        out["user_id"] = out["user_id"].strip()
    if "email" in out and isinstance(out["email"], str):
        out["email"] = out["email"].strip().lower()
    if "amount" in out:
        out["amount"] = round(float(out["amount"]), 2)
    if "tags" in out and isinstance(out["tags"], list):
        out["tags"] = sorted(set(out["tags"]))
    return out
