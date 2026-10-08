"""Problem 14 — The filter rules that had to be rewritten for every report
=========================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Every report needs a slightly different row filter:

    def vip_big(row):
        return row["tier"] == "vip" and row["amount"] > 1000

    def vip_big_recent(row):
        return row["tier"] == "vip" and row["amount"] > 1000 \\
            and row["days_ago"] < 30

Soon you have twenty near-identical functions, each hard-coding one
report's rules. Change one rule, edit twelve functions, miss one,
ship a wrong report.

Plain words: you own twenty coffee machines, each hard-wired to brew
exactly one drink. A new drink means buying a new machine.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The fraud team ships new detection rules weekly as config:

    rules:
      - field: amount, op: gt, value: 10000
      - field: country, op: ne, value: "US"
      - field: device_age_days, op: lt, value: 7

The old code needed a deploy for every rule change — a two-day
turnaround for a rule the fraud team wanted live in an hour. And
hand-written lambdas couldn't be serialized into the audit log, so
nobody could answer "which exact rules flagged this transaction?"

Your solution: ``build_predicate(rules)`` — a higher-order function
that turns rule dicts into ONE composable filter function:

  - each rule becomes a tiny lambda (``field``, ``op``, ``value``),
  - ``all_of(...)`` / ``any_of(...)`` combine them with AND / OR,
  - the builder also returns a human-readable description, so the
    audit log records exactly which rules ran.

Plain words: one espresso machine with dials. The fraud team turns
the dials (config); the machine (builder) brews whatever they asked
for — no new machine, no deploy, and the receipt lists the dials.

ANALOGY
-------
A bouncer with a printed checklist vs. a bouncer who memorized one
face. The checklist bouncer checks every rule on the card — change
the card, change the door policy tonight, and the card itself is the
record of who got turned away and why.
"""

from __future__ import annotations

import operator

_OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
    "in": lambda v, choices: v in choices,
    "not_in": lambda v, choices: v not in choices,
}


def _rule_fn(field, op, value):
    """Turn one rule dict into a tiny lambda over a row."""
    if op not in _OPS:
        raise ValueError(f"unknown op: {op!r}")
    test = _OPS[op]
    # Plain words: "does this row's field pass this one comparison?"
    return lambda row: test(row.get(field), value)


def all_of(*predicates):
    """Combine filters with AND — a row passes only if ALL pass."""
    return lambda row: all(p(row) for p in predicates)


def any_of(*predicates):
    """Combine filters with OR — a row passes if ANY passes."""
    return lambda row: any(p(row) for p in predicates)


def build_predicate(rules, mode="all"):
    """Build (predicate_fn, description) from a list of rule dicts.

    Each rule: {"field": ..., "op": "eq|ne|gt|ge|lt|le|in|not_in",
    "value": ...}. mode="all" requires every rule; mode="any"
    requires at least one. The description is audit-log ready.
    """
    fns = [_rule_fn(r["field"], r["op"], r["value"]) for r in rules]
    combiner = all_of if mode == "all" else any_of
    predicate = combiner(*fns) if fns else (lambda row: True)
    joiner = " AND " if mode == "all" else " OR "
    description = joiner.join(
        f"{r['field']} {r['op']} {r['value']!r}" for r in rules
    ) or "no rules (match all)"
    return predicate, description


def flag(rows, rules, mode="all"):
    """Return (flagged, audit) — flagged rows plus the exact rules used."""
    predicate, description = build_predicate(rules, mode)
    flagged = [r for r in rows if predicate(r)]
    audit = {"rules": description, "mode": mode,
             "flagged_count": len(flagged), "scanned": len(rows)}
    return flagged, audit


if __name__ == "__main__":
    txns = [
        {"id": 1, "amount": 50_000, "country": "NG", "device_age_days": 2},
        {"id": 2, "amount": 500, "country": "US", "device_age_days": 400},
        {"id": 3, "amount": 20_000, "country": "US", "device_age_days": 1},
    ]
    rules = [
        {"field": "amount", "op": "gt", "value": 10_000},
        {"field": "country", "op": "ne", "value": "US"},
        {"field": "device_age_days", "op": "lt", "value": 7},
    ]
    flagged, audit = flag(txns, rules)          # all three must hold
    print("flagged:", [t["id"] for t in flagged])  # [1]
    print("audit:", audit["rules"])

    # Same builder, OR mode — no new function, no deploy.
    flagged_any, _ = flag(txns, rules[:2], mode="any")
    print("any-mode:", [t["id"] for t in flagged_any])  # [1, 3]
