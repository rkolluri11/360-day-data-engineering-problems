"""Problem 3 — the idempotency key: charge once, answer forever
=============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A client posts "charge $50", the network drops the response,
and the client — correctly — retries the same request. Without
protection the second attempt charges $50 again:

    # NOT idempotent: retry -> double charge
    charge(amount)                # $50, then $50 again

With an idempotency key the server remembers the first answer
and replays it instead of re-executing:

    # idempotent: retry -> same receipt, one charge
    if key in charges:
        return charges[key]       # the ORIGINAL result
    charges[key] = charge(amount)

The client generates the key (one per INTENT, not per attempt)
and sends the same key on every retry. The server stores the
key with the result before answering.

Plain words: an idempotency key is a coat-check ticket. Hand
over the same ticket twice and you get the same coat back —
not a second coat, and not a charge for one.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The key must be created by the CALLER, once per intent.
    A server-generated key per attempt protects nothing: each
    retry is a brand-new key and a brand-new charge.
  - A replay with the same key but a DIFFERENT amount is a
    conflict, not a new charge. The safe answer is the original
    result (or an explicit conflict error) — never a second
    charge, never a silent overwrite of the first amount.
  - The key and its result must be stored ATOMICALLY with the
    side effect, or in the same transaction. Storing the key
    after the charge leaves a crash window where the charge
    happened but the key did not — the retry then double-
    charges. (This demo stores both in one dict write, which
    is atomic in-process; a real service uses a transaction.)
  - Keys must be retained at least as long as a client might
    retry — hours to days, not seconds. Evicting a key early
    re-opens the double-charge window.
  - Never reuse a key for a different intent. A recycled key
    returns someone else's receipt.

Your solution: ``process_charge`` and ``total_charged`` are
already written. The tests prove a same-key replay returns the
original charge id, charges once, and that a new key charges
again.

ANALOGY
-------
An idempotency key is a "one per customer" stamp on your hand
at a tasting. Show the stamp again and you get a smile, not a
second pour — and not a second bill.
"""


def process_charge(charges, key, amount):
    """Charge amount once per key; replays return the original result.

    ``charges`` maps idempotency key -> result dict. Returns the
    result dict: {"key", "charge_id", "amount", "status"}. A replay
    with the same key returns the stored result untouched, even
    if the caller passes a different amount this time.
    """
    if key in charges:
        return charges[key]
    result = {
        "key": key,
        "charge_id": f"ch-{len(charges) + 1:04d}",
        "amount": round(float(amount), 2),
        "status": "charged",
    }
    charges[key] = result
    return result


def total_charged(charges):
    """Total actually charged, counting each key exactly once."""
    return round(sum(r["amount"] for r in charges.values()), 2)
