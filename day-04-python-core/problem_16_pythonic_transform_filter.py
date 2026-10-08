"""Problem 16 — The two-pass loop that doubled the bill
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You have a list of raw event dictionaries from a clickstream feed:

    raw = [
        {"user": "u1", "amount_cents": 2500},
        {"user": "u2"},                      # malformed: no amount
        {"user": "u3", "amount_cents": 999},
    ]

You want clean records: only events that HAVE an amount, with the
amount converted from cents to dollars. The beginner version needs
two separate loops (or one loop with an ``if`` and an ``append``):

    clean = []
    for e in raw:
        if "amount_cents" in e:
            clean.append({"user": e["user"],
                          "amount_usd": e["amount_cents"] / 100})

Plain words: walk the pile, keep the good ones, reshape each one as
you keep it. A list comprehension says the same thing in one breath:

    [{"user": e["user"], "amount_usd": e["amount_cents"] / 100}
     for e in raw if "amount_cents" in e]

The ``if`` at the end is the filter; the expression at the front is
the transform. One pass, one new list.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your nightly job parses ~40 million raw order events. The original
code did the honest thing — filter in one loop, transform in a
second loop:

    valid = [e for e in raw if is_valid(e)]        # pass 1: 40M dicts
    clean = [to_record(e) for e in valid]          # pass 2: 40M dicts

That is 80 million dictionary allocations and two full walks over
the data before the load step even starts. On the billing dashboard
it shows up as a job that takes 2x the time and 2x the memory of
what the data actually needs — and at 3 AM it starts paging because
the worker keeps brushing against its memory limit.

Your solution: ``parse_orders(raw_events)`` — a single comprehension
that filters AND transforms in one pass, returning clean records:

    {"order_id": ..., "customer_id": ..., "amount_usd": ...,
     "event_time": ...}   # ISO timestamp, validated

Rules it enforces in that single pass:
  - drop events missing ``order_id`` or ``amount_cents``,
  - drop events where ``amount_cents`` is negative (refunds travel
    a different topic),
  - convert cents -> dollars as a float rounded to 2 decimals,
  - keep the original ``event_time`` string untouched.

Plain words: instead of sorting the mail into a "good" pile and then
re-reading the whole good pile to stamp each letter, you sort and
stamp in one motion as each letter passes your hands.

ANALOGY
-------
A factory line with two conveyor belts: belt one removes defective
parts, belt two paints the survivors. You pay for both belts, the
floor space, and every part rides twice. A list comprehension is one
belt with the inspector and the painter standing side by side.
"""

from __future__ import annotations


# --- BEFORE: the two-pass loop version -----------------------------------
# Plain words: readable, but every event is touched twice and held in
# memory twice. Fine for 1,000 rows; painful for 40 million.

def parse_orders_loop(raw_events):
    """Filter valid events, then transform — two passes, two lists."""
    valid = []
    for e in raw_events:
        if "order_id" in e and "amount_cents" in e and e["amount_cents"] >= 0:
            valid.append(e)
    clean = []
    for e in valid:
        clean.append({
            "order_id": e["order_id"],
            "customer_id": e.get("customer_id"),
            "amount_usd": round(e["amount_cents"] / 100, 2),
            "event_time": e.get("event_time"),
        })
    return clean


# --- AFTER: one pass, filter + transform together -------------------------
# Plain words: the `if` keeps only good events; the dict in front
# reshapes each survivor. One walk, one output list, half the garbage
# for the memory collector to sweep up.

def parse_orders(raw_events):
    """Parse raw order events in a single pass.

    Keeps events with an order_id and a non-negative amount_cents,
    converts cents to dollars, and returns clean record dicts.
    """
    return [
        {
            "order_id": e["order_id"],
            "customer_id": e.get("customer_id"),
            "amount_usd": round(e["amount_cents"] / 100, 2),
            "event_time": e.get("event_time"),
        }
        for e in raw_events
        if "order_id" in e
        and "amount_cents" in e
        and e["amount_cents"] >= 0
    ]


if __name__ == "__main__":
    raw = [
        {"order_id": "o1", "customer_id": "c9",
         "amount_cents": 2599, "event_time": "2026-10-06T20:00:00Z"},
        {"order_id": "o2", "customer_id": "c9"},              # no amount -> dropped
        {"order_id": "o3", "customer_id": "c4",
         "amount_cents": -500, "event_time": "2026-10-06T20:01:00Z"},  # refund -> dropped
        {"customer_id": "c1", "amount_cents": 100},          # no order_id -> dropped
    ]
    print(parse_orders(raw))
    # [{'order_id': 'o1', 'customer_id': 'c9', 'amount_usd': 25.99,
    #   'event_time': '2026-10-06T20:00:00Z'}]
    assert parse_orders(raw) == parse_orders_loop(raw)  # same answer, one pass
