"""Problem 3 — The validator with a hole in the middle
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
An ``if / elif / else`` chain answers one question: *which bucket
does this row belong in?* Beginners write chains with holes:

    if amount > 1000:
        flag = "review"
    elif amount > 0:
        flag = "ok"
    # amount <= 0 falls through... flag was never set -> NameError
    # three stages later.

Or they test truthiness when they mean existence:

    if row["discount"]:        # 0.0 discount is falsy -> treated as missing!

``0``, ``0.0``, ``""``, and ``[]`` are all falsy, but they're real
answers. "No discount" is not "unknown discount".

Plain words: a sorting chute needs a labeled bin for *every*
possible parcel, and "empty box" is different from "no box arrived".

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Every transaction entering the warehouse passes a validator that
must stamp exactly one verdict: ``ACCEPT``, ``QUARANTINE`` (looks
wrong, maybe recoverable — a human reviews it), or ``REJECT``
(structurally unusable — never let it near the fact table).

The old validator had two defects. First, ordering: it ran the
expensive timestamp parse *before* the cheap missing-field check,
so 40% of CPU went to parsing rows that were rejected anyway.
Second, a hole: negative amounts fell through every branch and
returned ``None``, which the loader read as "no verdict"... and
loaded them as sales. A partner sent ``-999.99`` "test" rows for
six days before finance noticed revenue dipping.

Your solution: ``classify_row(row)`` returns ``(verdict, reasons)``
with branches ordered cheapest-first and *exhaustive* — every
input lands in exactly one verdict, and the final ``else`` is a
safety net that can never be silently skipped:
  1. missing/blank required fields -> REJECT (cheapest: dict lookups)
  2. unknown currency code        -> REJECT
  3. amount unparseable or <= 0   -> QUARANTINE
  4. timestamp in the future      -> QUARANTINE
  5. amount above review limit    -> QUARANTINE
  6. else                        -> ACCEPT

Every existence check uses ``is None``, never truthiness, so a
``0.0`` amount is "zero" (quarantined) rather than "missing".

Plain words: parcels roll down the chute past the cheapest
sensors first, each sensor stamps exactly one bin, and the last
bin catches anything the sensors above somehow missed — nothing
falls on the floor.

ANALOGY
-------
A border checkpoint with lanes in order: no passport -> turned
away (fast); forged passport -> turned away; valid passport but
expired visa -> holding room; everything in order -> welcome
lane. Nobody walks past all the booths into the country
unstamped, and the officers check the cheap document glance
before the slow background check.
"""

from __future__ import annotations

from datetime import datetime, timezone

REQUIRED_FIELDS = ("transaction_id", "amount", "currency")

# ISO-4217 codes this pipeline settles in. Anything else is a
# partner typo until proven otherwise.
KNOWN_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD"}

# A single transaction above this goes to a human before it can
# move revenue numbers.
REVIEW_LIMIT = 1_000_000.0


def _parse_amount(value):
    """Parse an amount string; return (number, ok)."""
    if value is None:
        return None, False
    text = str(value).strip().replace("$", "").replace(",", "")
    if text == "" or text.lower() in {"n/a", "na", "null", "none"}:
        return None, False
    try:
        return float(text), True
    except ValueError:
        return None, False


def _parse_ts(value):
    """Parse an ISO-8601 timestamp; return (datetime, ok)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, False
    try:
        # fromisoformat can't read a trailing "Z"; normalize it.
        ts = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts, True
    except ValueError:
        return None, False


def classify_row(row):
    """Stamp one verdict on an inbound transaction row.

    Returns ``(verdict, reasons)`` where verdict is "ACCEPT",
    "QUARANTINE", or "REJECT" and reasons is a list of human-
    readable explanations. Branches run cheapest-first and the
    chain is exhaustive: there is no input without a verdict.
    """
    reasons = []

    # 1. Cheapest checks first: pure dict lookups, no parsing.
    # NOTE: `is None` and `== ""`, never `if not value` — a 0.0
    # amount or "0" id is data, not absence.
    for field in REQUIRED_FIELDS:
        value = row.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            reasons.append(f"missing required field: {field}")
    if reasons:
        return "REJECT", reasons

    # 2. Still cheap: a set membership test on the raw string.
    currency = str(row["currency"]).strip().upper()
    if currency not in KNOWN_CURRENCIES:
        return "REJECT", [f"unknown currency code: {row['currency']!r}"]

    # 3. First parse: amount. Unparseable or non-positive money is
    # suspicious but recoverable -> quarantine, not reject.
    amount, ok = _parse_amount(row["amount"])
    if not ok:
        return "QUARANTINE", [f"amount not parseable: {row['amount']!r}"]
    if amount <= 0:
        reasons.append(f"non-positive amount: {amount}")
        return "QUARANTINE", reasons

    # 4. Timestamp parse only happens for rows that survived 1-3,
    # so we never pay for parsing rows we'd reject anyway.
    event_ts, ok = _parse_ts(row.get("event_ts"))
    if ok and event_ts > datetime.now(timezone.utc):
        return "QUARANTINE", [f"event timestamp in the future: {row['event_ts']!r}"]

    # 5. Whale check: real money, but big enough for human eyes.
    if amount > REVIEW_LIMIT:
        return "QUARANTINE", [f"amount {amount:,.2f} exceeds review limit"]

    # 6. Exhaustive else: survived every sensor -> welcome lane.
    return "ACCEPT", []


def classify_batch(rows):
    """Split rows into accepted / quarantined / rejected buckets."""
    buckets = {"ACCEPT": [], "QUARANTINE": [], "REJECT": []}
    for row in rows:
        verdict, reasons = classify_row(row)
        buckets[verdict].append((row, reasons))
    return buckets


if __name__ == "__main__":
    batch = [
        {"transaction_id": "T-1", "amount": "42.50", "currency": "USD",
         "event_ts": "2026-10-06T10:00:00Z"},
        {"transaction_id": "T-2", "amount": "", "currency": "USD"},          # missing
        {"transaction_id": "T-3", "amount": "15.00", "currency": "XYZ"},     # bad code
        {"transaction_id": "T-4", "amount": "-999.99", "currency": "EUR"},   # negative
        {"transaction_id": "T-5", "amount": "5.00", "currency": "USD",
         "event_ts": "2099-01-01T00:00:00Z"},                               # future
        {"transaction_id": "T-6", "amount": "2500000", "currency": "USD"},  # whale
        {"transaction_id": "T-7", "amount": "0", "currency": "USD"},        # zero, not missing
    ]
    for row in batch:
        verdict, reasons = classify_row(row)
        print(f"{row['transaction_id']}: {verdict} {reasons}")
