"""Problem 5 — The two tenants who shared one brain
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
In Python, a variable is a *name tag tied to an object*, not a box
holding a value. So:

    a = [1, 2]
    b = a          # b is a second tag on the SAME list
    b.append(3)
    print(a)       # [1, 2, 3] — surprise!

``b = a`` copied the tag, not the list. And ``==`` asks "same
*contents*?", while ``is`` asks "same *object*?":

    [1, 2] == [1, 2]    # True  (equal contents)
    [1, 2] is [1, 2]    # False (two different objects)

Beginners also write ``if x == None`` — which calls a custom
``__eq__`` and can lie — instead of ``if x is None``.

Plain words: two name tags can point at one dog. Rename the dog
through one tag and the other tag sees it too. ``==`` asks "same
breed?", ``is`` asks "same dog?".

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A multi-tenant ingestion service keeps one default pipeline config:

    DEFAULTS = {"batch_size": 10_000, "retries": 3,
                "columns": ["txn_id", "amount", "currency"]}

and "customizes" it per tenant:

    cfg = DEFAULTS            # alias, not a copy!
    cfg["batch_size"] = 500   # tenant Acme wants small batches

Tenant Acme's tuning silently rewrote the *shared* defaults —
including the nested ``columns`` list, which ``dict(cfg)`` (a
shallow copy) would *still* share. The next tenant onboarded with
``batch_size = 500`` and a ``columns`` list that another tenant
had appended debug columns to. Settlement reports drifted for
days; every tenant's config looked right in isolation.

Your solution in this file:
  - ``make_default_config()`` — builds a FRESH config dict (and a
    fresh ``columns`` list) on every call, so no two tenants can
    ever share one;
  - ``register_tenant(registry, name, overrides=None)`` — deep-
    enough copy of defaults plus overrides; ``overrides=None``
    handled with ``is None`` (never a mutable default argument,
    never ``== None``);
  - ``resolve_option(value, default)`` — ``None`` means "unset",
    everything else (including ``0``) is a real choice;
  - ``dedupe_rows(rows)`` — drop duplicate rows by *equality*
    (``==``), keeping the first occurrence — the value-vs-identity
    distinction doing honest work.

Plain words: every tenant gets their own printed form *and* their
own stapled appendix — never one shared form passed around the
office. "Left blank" (None) falls back to the default; "wrote 0"
stays 0.

ANALOGY
-------
A landlord photocopying the lease for each tenant versus handing
every tenant the same single sheet to write on. With one shared
sheet, tenant B's pet clause becomes tenant A's pet clause. The
fix is obvious once you see it: photocopy the whole thing —
appendix pages included — before anyone picks up a pen.
"""

from __future__ import annotations

import copy


def make_default_config():
    """Build a brand-new default pipeline config.

    Plain words: a fresh photocopy every time — callers can scribble
    on it freely without touching anyone else's.
    """
    return {
        "batch_size": 10_000,
        "retries": 3,
        "timeout_secs": 30,
        "on_error": "quarantine",
        "columns": ["txn_id", "amount", "currency"],
    }


def register_tenant(registry, name, overrides=None):
    """Register a tenant with its own independent config.

    Copies the defaults (deep enough to detach the nested
    ``columns`` list), applies ``overrides``, and stores the result
    under ``name``. ``overrides`` defaults to ``None`` — the
    sentinel is checked with ``is None``, so a caller passing an
    empty dict keeps it (and we never grow a shared mutable
    default argument across calls).
    """
    # `is None`, not `== None` and not `if not overrides`: an
    # explicit {} is a real choice, and __eq__ could lie.
    if overrides is None:
        overrides = {}
    config = copy.deepcopy(make_default_config())
    for key, value in overrides.items():
        # Copy mutable override values too, so the caller's list
        # can't stay aliased to the tenant's config later.
        config[key] = copy.deepcopy(value)
    registry[name] = config
    return config


def resolve_option(value, default):
    """Return ``default`` only when ``value`` is None.

    Plain words: blank means "you decide"; 0, "", and False are
    deliberate answers and survive.
    """
    return default if value is None else value


def get_batch_size(registry, name):
    """Look up a tenant's batch size, falling back to 10_000.

    A tenant that explicitly set ``batch_size = 0`` ("no batching")
    keeps 0 — the fallback only fires on None/missing.
    """
    config = registry.get(name)
    if config is None:
        return 10_000
    return resolve_option(config.get("batch_size"), 10_000)


def same_object(a, b):
    """Identity check: are these two names tied to one object?"""
    return a is b


def dedupe_rows(rows):
    """Drop duplicate rows by equality, keeping first occurrences.

    Two rows that are ``==`` but distinct objects collapse to one;
    order is preserved. (For unhashable rows like dicts this is
    O(n^2) — fine for quarantine-sized lists, not for millions.)
    """
    unique = []
    for row in rows:
        # `==` compares contents; `is` would only catch the exact
        # same object, missing every real duplicate.
        if not any(row == seen for seen in unique):
            unique.append(row)
    return unique


if __name__ == "__main__":
    registry = {}
    register_tenant(registry, "acme", {"batch_size": 500})
    register_tenant(registry, "globex")  # defaults

    # Acme's tuning must not leak into anyone else.
    registry["acme"]["columns"].append("debug_flag")
    print("acme batch:", get_batch_size(registry, "acme"))      # 500
    print("globex batch:", get_batch_size(registry, "globex"))  # 10000
    print("globex columns:", registry["globex"]["columns"])     # no debug_flag

    # Identity vs equality in one line:
    a = ["txn_id", "amount"]
    b = ["txn_id", "amount"]
    print("== :", a == b, " is:", same_object(a, b))  # True, False

    rows = [{"id": 1}, {"id": 2}, {"id": 1}, {"id": 3}, {"id": 2}]
    print("deduped:", dedupe_rows(rows))
