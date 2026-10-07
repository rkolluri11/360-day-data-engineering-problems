"""Problem 4 — The tenant config that leaked
========================================

THE PROBLEM (beginner foothold first)
------------------------------------
Bake a tax rate into a function:

    def make_tax(rate):
        return lambda amount: amount * rate

``make_tax(0.07)`` returns a function that adds 7% tax. The lambda
*closes over* ``rate`` — it remembers the value from when it was
made. That remembered value is a closure.

Plain words: a recipe card with one line pre-filled in ink. Every
copy made from it carries that line.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your pipeline serves 30 tenants. Each tenant gets a transform with
baked-in config: tax rate, required fields, currency rounding.

    tenant_a = make_transform(rate=0.07, required_fields=["id"])
    tenant_b = make_transform(rate=0.20, required_fields=["id", "vat"])

At 2 AM, tenant A's ``required_fields`` suddenly contains ``"vat"``.
What happened: the factory stored the *same list object* in both
transforms, and tenant B's onboarding code appended to it. The
closure remembered the *object*, not a snapshot.

Your solution: ``make_transform(**defaults)`` returns
``transform(row, **overrides)`` such that:

  1. defaults are deep-copied at build time — tenants can never
     share mutable config, even lists/dicts nested inside;
  2. per-call ``overrides`` merge over the bound config WITHOUT
     mutating it — one call's override never leaks into the next;
  3. ``transform.with_config(**extra)`` returns a NEW transform
     with merged config; the original is untouched (currying);
  4. ``transform.config()`` returns a snapshot of the bound config;
  5. missing required inputs raise clear errors: no ``rate`` bound
     and no ``rate`` override -> ``KeyError``; a row missing a
     required field -> ``ValueError`` naming the field.

Plain words: every tenant gets their own printed recipe card, not
a shared whiteboard. Writing on your card — or scribbling a
one-time note for tonight's order — never changes anyone else's.

ANALOGY
-------
A coffee shop's recipe book: the house latte card says "2 shots".
The airport branch's card was *photocopied* from it, then someone
penciled "3 shots" on the airport copy. The house card must still
say 2 — and tonight's "extra hot" request for one customer must
not become tomorrow's default.
"""

from __future__ import annotations

import copy


def make_transform(**defaults):
    """Build a row transform with config baked in, safely isolated.

    The returned ``transform(row, **overrides)`` applies the bound
    config (tax rate, required fields) to each row. All config is
    deep-copied at build time and per call, so tenants and calls
    can never leak state into each other.
    """
    bound = copy.deepcopy(defaults)

    def transform(row, **overrides):
        cfg = copy.deepcopy(bound)
        cfg.update(copy.deepcopy(overrides))

        if "rate" not in cfg:
            raise KeyError("transform needs a 'rate' (bind it or pass per call)")
        rate = cfg["rate"]

        missing = [f for f in cfg.get("required_fields", []) if f not in row]
        if missing:
            raise ValueError(f"row missing required field(s): {missing}")

        out = dict(row)
        if "total" in row:
            rounded = round(row["total"] * (1 + rate), cfg.get("ndigits", 2))
            out["taxed_total"] = rounded
        return out

    def with_config(**extra):
        merged = copy.deepcopy(bound)
        merged.update(copy.deepcopy(extra))
        return make_transform(**merged)

    def snapshot():
        return copy.deepcopy(bound)

    transform.with_config = with_config
    transform.config = snapshot
    return transform


if __name__ == "__main__":
    tenant_a = make_transform(rate=0.07, required_fields=["id"])
    tenant_b = make_transform(rate=0.20, required_fields=["id", "vat"])

    # Tenant B appends to its own list — tenant A must not see it.
    tenant_b.config()["required_fields"].append("sneaky")
    print("A fields:", tenant_a.config()["required_fields"])
    print("B fields:", tenant_b.config()["required_fields"])

    row = {"id": 1, "total": 100.0}
    print(tenant_a(row))
    print(tenant_a(row, rate=0.10))   # one-time override...
    print(tenant_a(row))              # ...does not stick
    print(tenant_a.with_config(rate=0.15)(row))  # curried copy
    print(tenant_a(row))              # original untouched
