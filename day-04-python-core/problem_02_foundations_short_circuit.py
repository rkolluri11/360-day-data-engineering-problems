"""Problem 2 — The filter that crashed before it could say no
========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``and`` and ``or`` don't just return ``True``/``False`` — they return
one of their *operands*, and they stop early (short-circuit):

    0 or "default"        # -> "default"  (0 is falsy, keep looking)
    "hi" or "default"     # -> "hi"       (found a truthy one, stop)
    1 and 2               # -> 2          (both truthy, return the last)

Two traps follow. First, ``or`` as a default eats *valid* falsy
values: ``quantity = row["qty"] or 1`` turns a legitimate ``0``
into ``1``. Second, order matters for safety:

    float(row["amount"]) > 0 and row["amount"] is not None

calls ``float(None)`` and explodes — the guard came *after* the
dangerous call instead of before it.

Plain words: ``and``/``or`` are bouncers who stop checking the
moment the answer is decided. Put the cheap, safe check first and
the expensive, dangerous one last — and never use ``or`` to fill
a default when ``0`` or ``""`` is a real answer.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A revenue feed filter decides which transactions flow into the
daily USD settlement report:

    keep if amount parses AND amount > 0 AND currency in ("USD", "EUR")

The first version was written as:

    def keep(row):
        return float(row["amount"]) > 0 and row["currency"] in ("USD", "EUR")

Rows with ``amount = ""`` raised ``ValueError`` and killed the
whole report. The "fix" used ``or`` defaults:

    amount = float(row["amount"] or 0)   # "" -> 0, fine...

but a second rule, ``min_qty = row["min_qty"] or 10``, silently
turned an explicit ``min_qty = 0`` ("no minimum") into ``10``,
dropping thousands of valid micro-transactions for a week.

Your solution in this file:
  - ``safe_float(value)`` — parses or returns ``None``, never raises;
  - ``is_valid_amount(value)`` — guard clauses first: reject
    ``None``/``""`` *before* touching ``float()``;
  - ``with_default(value, default)`` — substitutes only for ``None``,
    so real ``0`` and ``""`` survive;
  - ``all_of(*preds)`` / ``any_of(*preds)`` — combine row
    predicates with true short-circuiting (expensive checks never
    run once the answer is decided).

Plain words: the bouncers check ID (cheap, safe) before the
full-body scan (expensive, can fail). And the coat check only
hands you a spare coat if you arrived with *no* coat — not if
you arrived wearing a thin one.

ANALOGY
-------
Airport security: you show your boarding pass (fast, harmless)
*before* anyone opens your bag (slow, can go wrong). Nobody opens
the bag of a passenger with no boarding pass — they're turned
away at the first desk. And if you declare zero bags, the agent
doesn't write down "one bag" for you.
"""

from __future__ import annotations


def safe_float(value):
    """Parse to float; return None instead of raising.

    Plain words: try the risky conversion, but hand back an
    empty-handed "no value" instead of blowing up the caller.
    """
    if value is None:
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    if text == "" or text.lower() in {"n/a", "na", "null", "none"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def is_valid_amount(value):
    """True only for a parseable number strictly greater than zero.

    Guard order is the whole point: the ``None``/blank check runs
    first so ``float()`` never sees a value it would choke on.
    """
    # Cheap, safe bouncer first — never call float() on these.
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    amount = safe_float(value)   # expensive/dangerous call goes last
    return amount is not None and amount > 0


def with_default(value, default):
    """Return ``default`` only when ``value`` is None.

    Plain words: unlike ``value or default``, this keeps real
    answers like 0, 0.0, "", and False untouched.
    """
    return default if value is None else value


def all_of(*predicates):
    """Combine predicates with AND; short-circuits on first False.

    Returns a predicate ``f(row)``. Because Python's ``and``
    short-circuits, an expensive predicate never runs once an
    earlier one already said no.
    """
    def combined(row):
        for pred in predicates:
            if not pred(row):
                return False
        return True
    return combined


def any_of(*predicates):
    """Combine predicates with OR; short-circuits on first True."""
    def combined(row):
        for pred in predicates:
            if pred(row):
                return True
        return False
    return combined


def make_settlement_filter(currencies=("USD", "EUR")):
    """Keep rows eligible for the daily settlement report.

    A row is kept when its amount is a valid positive number AND
    its currency is in the allowed set. The amount guard runs
    first, so malformed amounts can't crash the currency check.
    """
    allowed = set(currencies)

    def amount_ok(row):
        return is_valid_amount(row.get("amount"))

    def currency_ok(row):
        code = row.get("currency")
        return isinstance(code, str) and code.strip().upper() in allowed

    return all_of(amount_ok, currency_ok)


if __name__ == "__main__":
    feed = [
        {"txn": "T1", "amount": "$12.50", "currency": "USD"},
        {"txn": "T2", "amount": "", "currency": "USD"},       # blank amount
        {"txn": "T3", "amount": "-4.00", "currency": "USD"},   # refund, not sale
        {"txn": "T4", "amount": "9.99", "currency": "JPY"},    # wrong currency
        {"txn": "T5", "amount": None, "currency": "EUR"},      # missing amount
        {"txn": "T6", "amount": "20", "currency": "eur"},      # lowercase code
    ]
    keep = make_settlement_filter()
    print("kept:", [r["txn"] for r in feed if keep(r)])  # T1, T6
    print("with_default(0, 10) =", with_default(0, 10))   # 0, not 10
    print("with_default(None, 10) =", with_default(None, 10))  # 10
