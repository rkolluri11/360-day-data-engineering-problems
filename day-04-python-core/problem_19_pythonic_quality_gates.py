"""Problem 19 — The gate that scanned 10 million rows to say no
========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
"Are all the scores passing?" The beginner writes a flag loop:

    ok = True
    for s in scores:
        if s < 60:
            ok = False
            break

Plain words: walk the list, flip the flag the moment you see a
failure. ``all()`` IS that loop, built in:

    all(s >= 60 for s in scores)     # True only if every score passes
    any(s < 60 for s in scores)      # True if even one fails

``all`` stops at the first failure; ``any`` stops at the first
success. They short-circuit — they don't finish the walk once the
answer is known.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Before the 7 AM executive dashboard refreshes, a gate job must
certify the overnight partition: 10 million rows. Two checks:

  1. COMPLETENESS — every expected source file landed
     (``all(f["landed"] for f in manifest)``).
  2. CONTRACT — no row carries a null primary key, and no row
     carries a negative amount.

The original gate looped over all 10M rows building a list of
booleans FIRST, then checked it:

    checks = [row["order_id"] is not None for row in rows]  # 10M bools!
    ok = all(checks)

Two problems: it materialized 10 million booleans just to ask a
yes/no question, and when row 12 was already corrupt, it still
scanned the other 9,999,988 rows before answering "no" — the
dashboard waited 20 extra minutes for an answer that was known
in the first second.

Your solution: ``partition_ready(manifest, rows)`` —
  - ``all(...)`` over the small manifest for completeness,
  - ``any(...)`` over a GENERATOR of violations for the contract,
    so the first bad row stops the scan immediately and nothing
    but one boolean stream is ever materialized.

It returns ``(ready: bool, reason: str)`` — because a gate that
only says "no" without saying WHY gets ignored by on-call.

Plain words: instead of photographing every page of a 10,000-page
contract before checking the signature, you read until you find
the first unsigned page, then stop and report the page number.

ANALOGY
-------
Airport security: `any()` is the metal detector — one beep and
you're pulled aside; it doesn't finish scanning the whole line
first. `all()` is the boarding check — every passenger needs a
boarding pass, and the first one without stops the line.
"""

from __future__ import annotations


# --- BEFORE: materialize-then-check ---------------------------------------
# Plain words: builds a 10-million-item list of True/False just to ask
# one yes/no question, and never stops early. Slow AND wasteful.

def gate_eager(manifest, rows):
    """Check the partition by materializing every check first."""
    landed = [f["landed"] for f in manifest]
    keys_ok = [r.get("order_id") is not None for r in rows]
    amounts_ok = [r.get("amount_cents", 0) >= 0 for r in rows]
    if not all(landed):
        return False, "missing source files"
    if not all(keys_ok):
        return False, "null order_id found"
    if not all(amounts_ok):
        return False, "negative amount found"
    return True, "partition certified"


# --- AFTER: short-circuiting gates over generators -------------------------
# Plain words: `any()` walks the violation stream and quits at the
# first bad row. No boolean list is ever built; a corrupt row 12
# means rows 13..10M are never even looked at.

def _violations(rows):
    """Yield (row_number, reason) for each contract violation, lazily."""
    for i, r in enumerate(rows):
        if r.get("order_id") is None:
            yield i, "null order_id"
        elif r.get("amount_cents", 0) < 0:
            yield i, "negative amount"


def partition_ready(manifest, rows):
    """Certify a partition with short-circuiting quality gates.

    Returns (True, "partition certified") or (False, reason naming
    the first failure found). Stops scanning at the first problem.
    """
    missing = [f["name"] for f in manifest if not f.get("landed")]
    if missing:
        return False, f"missing source files: {missing[0]}"

    bad = next(_violations(rows), None)  # first violation only; stops early
    if bad is not None:
        row_no, reason = bad
        return False, f"row {row_no}: {reason}"
    return True, "partition certified"


def has_pii_leak(rows):
    """True the moment ANY row exposes an unmasked email."""
    return any(r.get("email", "").find("@") != -1
               and not r.get("email_masked", False)
               for r in rows)


if __name__ == "__main__":
    manifest = [{"name": "orders.csv", "landed": True},
                {"name": "customers.csv", "landed": True}]
    rows = ({"order_id": f"o{i}", "amount_cents": 100} for i in range(5))
    print(partition_ready(manifest, rows))  # (True, 'partition certified')

    bad_rows = [{"order_id": "o1", "amount_cents": 100},
                {"order_id": None, "amount_cents": 50}]
    print(partition_ready(manifest, bad_rows))  # (False, 'row 1: null order_id')

    print(has_pii_leak([{"email": "a@x.com", "email_masked": True}]))   # False
    print(has_pii_leak([{"email": "a@x.com", "email_masked": False}]))  # True
