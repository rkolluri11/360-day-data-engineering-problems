"""Problem 4 — quarantine, don't crash: bad rows route, the batch survives
==========================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
One malformed row — ``amount: "abc"`` — and the naive transform raises,
killing all 999,999 good rows with it. The pipeline pattern is SPLIT,
not STOP: every row lands in exactly one of two buckets:

    clean, quarantined = clean_batch(rows)

Quarantined rows carry their reason: ``{"_row": {...}, "_reason":
"bad_amount:'abc'"}``. The batch finishes; the bad rows wait in a side
file for a human, with the evidence attached.

Plain words: quarantine is airport secondary screening — the suspicious
bag goes to the side room with a tag explaining why, and the flight
still departs on time.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The ORDER of checks is the contract: missing order_id first (no key,
    no identity), then unparseable amount, then absent amount, then
    negative amount (a business rule — refunds flow through a different
    stage). Each reason string names the failure precisely; a downstream
    analyst triages from the reason column alone.
  - ``clean_batch`` must NEVER raise on row data: no key, wrong type,
    hostile string — everything routes. (It may still raise on a
    non-iterable input; that's a caller bug, not row data.)
  - Clean rows come out NORMALIZED: ``amount`` is a real float, so no
    downstream stage re-parses strings. Quarantined ``_row`` entries are
    COPIES — the caller's input batch is never mutated.
  - Test the routing, not just the happy path: the suite asserts each
    bad row lands in quarantine with the EXACT reason, good rows parse,
    and the input batch is untouched.

Your solution: ``clean_batch(rows)`` below (reuses problem 2's parser).
Then run the tests: ``python -m pytest tests -q`` from the day-14 folder.

ANALOGY
-------
Splitting good and bad rows is sorting mail: letters with a valid
address go in the delivery sack; the ones with no address go to the dead
letter office WITH the envelope intact — nobody burns the whole sack
because of one bad address.
"""

from problem_02_parametrize_the_boundary import parse_amount


def clean_batch(rows):
    """Split rows into (clean, quarantined).

    Clean rows: {"order_id", "amount" (float), "status"}.
    Quarantined: {"_row": <copy of original>, "_reason": <precise reason>}.
    Never raises on row data; never mutates the input batch.
    """
    clean, quarantined = [], []
    for row in rows:
        order_id = row.get("order_id")
        if not order_id:
            quarantined.append({"_row": dict(row), "_reason": "missing:order_id"})
            continue
        try:
            amount = parse_amount(row.get("amount"))
        except ValueError:
            quarantined.append(
                {"_row": dict(row), "_reason": f"bad_amount:{row.get('amount')!r}"}
            )
            continue
        if amount is None:
            quarantined.append({"_row": dict(row), "_reason": "missing:amount"})
            continue
        if amount < 0:
            quarantined.append(
                {"_row": dict(row), "_reason": f"negative_amount:{amount}"}
            )
            continue
        clean.append({"order_id": order_id, "amount": amount,
                      "status": row.get("status")})
    return clean, quarantined
