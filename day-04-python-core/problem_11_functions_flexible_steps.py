"""Problem 11 — The dispatcher that had to learn every step's signature
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You write a helper that runs pipeline steps:

    def run(step, rows):
        return step(rows)

Then someone writes a step needing a threshold:

    def drop_small(rows, min_amount):
        ...

Your helper can't call it — ``run(drop_small, rows)`` crashes with a
missing argument. So you change the helper for this one step... then
the next step needs two knobs, then a flag, then a callback. Every new
step forces you to edit the dispatcher. The dispatcher has to "know"
every step in the building.

Plain words: the dispatcher is a receptionist who insists on knowing
every visitor's full life story before letting them upstairs. New
visitor, new interrogation.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your team ships a plugin-style pipeline: data scientists drop new
step functions into a ``steps/`` folder, and a nightly job runs them
all in order. Steps have wildly different signatures:

    def dedupe(rows): ...
    def cap_amount(rows, max_amount, *, currency="USD"): ...
    def tag_vip(rows, vip_ids, tag="vip", notify=None): ...

The old dispatcher enumerated every parameter by hand and broke on
every new plugin. Worse, ops needed to pass an emergency ``dry_run``
flag through to *all* steps, and half the steps didn't accept it.

Your solution: ``call_step(step_fn, rows, *args, **kwargs)`` — a thin
dispatcher that forwards whatever it receives, untouched:

  - extra positional/keyword arguments pass straight through, so a
    step with new knobs works without the dispatcher ever changing,
  - steps that don't declare a knob simply don't receive it, via a
    registry wrapper that only forwards what each step accepts,
  - the ops-level ``run_all(steps, rows, **shared)`` broadcasts shared
    knobs (like ``dry_run=True``) to whichever steps declare them.

Plain words: the receptionist stops interrogating and just hands over
the sealed envelope. The envelope goes to the visitor unopened — and
if the visitor's door doesn't take envelopes, the receptionist only
passes along the letters that fit the slot.

ANALOGY
-------
A universal TV remote vs. a drawer of single-device remotes. The
universal remote forwards whatever buttons you press; it never needs
to learn each TV's menu first. New TV on the shelf? Same remote.
"""

from __future__ import annotations

import inspect


def call_step(step_fn, rows, *args, **kwargs):
    """Call a step, forwarding every extra argument untouched.

    The dispatcher never inspects or rewrites arguments — a step with
    a brand-new knob works the day it is written, with zero changes
    here.
    """
    return step_fn(rows, *args, **kwargs)


def _accepts(step_fn, name):
    """True if the step declares parameter `name` (or **kwargs)."""
    params = inspect.signature(step_fn).parameters.values()
    return any(
        p.name == name or p.kind == inspect.Parameter.VAR_KEYWORD
        for p in params
    )


def _positional_capacity(step_fn):
    """How many extra positional args the step can take (beyond rows)."""
    params = list(inspect.signature(step_fn).parameters.values())
    capacity = 0
    for p in params[1:]:  # skip `rows`
        if p.kind == inspect.Parameter.VAR_POSITIONAL:
            return float("inf")
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                      inspect.Parameter.POSITIONAL_OR_KEYWORD):
            capacity += 1
        else:
            break
    return capacity


def run_all(steps, rows, *args, **shared):
    """Run every step in order, forwarding only the knobs each accepts.

    ``*args`` go to steps with positional capacity; ``**shared``
    knobs (e.g. dry_run=True) go only to steps that declare them, so
    an ops-wide flag never crashes a step that doesn't know it.
    """
    current = rows
    for step_fn in steps:
        cap = _positional_capacity(step_fn)
        fwd_args = args[:cap] if cap != float("inf") else args
        fwd_kwargs = {k: v for k, v in shared.items()
                      if _accepts(step_fn, k)}
        current = step_fn(current, *fwd_args, **fwd_kwargs)
    return current


# --- Example plugin steps ------------------------------------------------

def dedupe(rows):
    """Drop duplicate rows, keeping first occurrence."""
    seen, out = set(), []
    for r in rows:
        key = tuple(sorted(r.items()))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def cap_amount(rows, max_amount, *, currency="USD", dry_run=False):
    """Cap transaction amounts; dry_run reports without changing rows."""
    capped = [{**r, "amount": min(r["amount"], max_amount),
               "currency": currency} for r in rows]
    changed = sum(1 for a, b in zip(rows, capped) if a != b)
    if dry_run:
        return {"would_change": changed, "rows": rows}
    return capped


def tag_vip(rows, vip_ids, tag="vip"):
    """Tag rows whose customer id is in the VIP set."""
    return [{**r, "tags": ([tag] if r.get("customer") in vip_ids else [])}
            for r in rows]


if __name__ == "__main__":
    rows = [
        {"customer": "a1", "amount": 500},
        {"customer": "a1", "amount": 500},   # duplicate
        {"customer": "b2", "amount": 50_000},
    ]
    # New-style dispatch: the dispatcher never learned these signatures.
    print(call_step(dedupe, rows))
    print(call_step(cap_amount, rows, 1_000, currency="EUR"))

    steps = [dedupe, cap_amount, tag_vip]
    # Shared knobs as KEYWORDS: each step receives only what it declares
    # (cap_amount takes max_amount; tag_vip takes vip_ids; dedupe takes
    # neither) — no positional mix-ups across different signatures.
    out = run_all(steps, rows, max_amount=1_000, vip_ids={"a1"})
    print(out)  # capped + tagged; dry_run=False default, real transform

    # Ops broadcast: dry_run=True reaches cap_amount only (dedupe/tag_vip
    # don't declare it, so they never crash on the unknown knob).
    out2 = run_all([dedupe, tag_vip], rows, vip_ids={"a1"}, dry_run=True)
    print(out2)  # same as without dry_run — unknown knobs ignored safely
