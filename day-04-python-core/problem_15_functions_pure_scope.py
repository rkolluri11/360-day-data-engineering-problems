"""Problem 15 — The FX step whose tests passed on Monday and failed on Friday
===============================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A transform reads a global and mutates another:

    RATE = 1.08
    ERRORS = []

    def to_eur(row):
        ERRORS.append(row) if row["amount"] < 0 else None
        return row["amount"] * RATE

Tests pass in isolation. Run the whole suite and they fail — some
earlier test changed ``RATE`` or left junk in ``ERRORS``. The
function's answer depends on invisible roommates, not just its
arguments.

Plain words: the function is a cook who seasons "to taste" from
whoever's spice rack is nearest. Same recipe, different kitchen,
different dish — and you can't write a recipe test for "to taste."

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The revenue pipeline's FX step did three spooky things:

1. It read the exchange rate from a module-level global refreshed by
   a background thread — mid-batch refreshes converted half a file
   at Monday's rate and half at Tuesday's. The totals never
   reconciled, and reruns produced different numbers.
2. It appended bad rows to a global ``_ERRORS`` list — the second
   file's error report contained the first file's errors, and a
   retry double-counted.
3. Nobody could unit-test it without monkeypatching globals, so the
   step shipped with zero meaningful tests.

Your solution: ``convert_batch(rows, rate)`` — a PURE function.
The rate arrives as an explicit argument (same input, same output,
every time), and errors come back as a return value instead of a
global side effect:

    converted, errors = convert_batch(rows, rate=1.08)

Deterministic, rerunnable, trivially testable. A thin impure shell
(``run_fx``) fetches the live rate ONCE per batch and calls the pure
core — impurity lives at the edges, logic stays pure.

Plain words: the cook now gets the exact grams of salt handed over
with the recipe, and puts scraps in a returned tray instead of a
shared bin. Same ingredients in, same dish out — in any kitchen.

ANALOGY
-------
A vending machine vs. a tip jar with a "take what you need" sign.
The vending machine takes exact coins (arguments) and returns exact
change (return value) — testable, predictable. The tip jar's outcome
depends on who touched it last. Production code should vend, not jar.
"""

from __future__ import annotations


def convert_batch(rows, rate):
    """Convert USD amounts to EUR — pure: no globals read or written.

    Returns (converted, errors): converted rows carry ``amount_eur``;
    rows with missing/negative amounts land in errors with a reason.
    Same inputs always give same outputs.
    """
    converted, errors = [], []
    for row in rows:
        amount = row.get("amount_usd")
        # Plain words: bad money goes to the error tray, never the total.
        if not isinstance(amount, (int, float)) or amount < 0:
            errors.append({**row, "reason": "bad amount_usd"})
            continue
        converted.append({**row, "amount_eur": round(amount * rate, 2)})
    return converted, errors


def summarize(converted):
    """Pure total over converted rows — safe to call anywhere, anytime."""
    return {
        "rows": len(converted),
        "total_eur": round(sum(r["amount_eur"] for r in converted), 2),
    }


def run_fx(rows, rate_source):
    """Impure shell: fetch the live rate ONCE, then run the pure core.

    ``rate_source`` is a zero-arg callable (API, cache, config).
    Fetching once per batch means one file never straddles two rates.
    """
    rate = rate_source()  # the ONLY impure line in the batch path
    converted, errors = convert_batch(rows, rate)
    return {
        "converted": converted,
        "errors": errors,
        "summary": summarize(converted),
        "rate_used": rate,
    }


if __name__ == "__main__":
    rows = [
        {"id": 1, "amount_usd": 100},
        {"id": 2, "amount_usd": -5},    # bad -> errors
        {"id": 3, "amount_usd": 250},
    ]
    # Deterministic: same inputs, same outputs — rerun-proof.
    c1, e1 = convert_batch(rows, 1.08)
    c2, e2 = convert_batch(rows, 1.08)
    print("deterministic:", c1 == c2 and e1 == e2)  # True
    print("summary:", summarize(c1))               # 2 rows, 378.0 EUR

    # The shell fetches the rate once per batch — no mid-batch flip.
    calls = {"n": 0}

    def fake_rate_source():
        calls["n"] += 1
        return 1.10

    out = run_fx(rows, fake_rate_source)
    print("rate fetched times:", calls["n"])  # 1
    print("rate used:", out["rate_used"], "| errors:", len(out["errors"]))
