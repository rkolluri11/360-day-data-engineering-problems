"""Problem 2 — Parentheses, not brackets
=======================================

THE PROBLEM (beginner foothold first)
------------------------------------
List comprehensions are Python's favorite one-liner:

    total = sum([float(r["amt"]) for r in rows if r["ok"]])

The brackets build the *entire* filtered list in memory first, then
``sum`` walks it. Two passes, one full copy of the data.

Swap the brackets for parentheses and the same expression becomes a
*generator expression* — lazy:

    total = sum(float(r["amt"]) for r in rows if r["ok"])

Now ``sum`` pulls one item at a time. The intermediate list never
exists. Same result, one pass, flat memory.

Plain words: brackets = build the whole pile, then count it.
Parentheses = count as items roll past.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Generator expressions have sharp edges that show up in pipelines:

  - They are single-use. ``vals = (f(x) for x in src)``; iterating
    ``vals`` twice gives you data the first time and *nothing* the
    second time. If a downstream stage re-iterates, totals silently
    become zero.
  - ``len()`` doesn't exist on them. Code that checks "did we get any
    rows?" with ``len`` crashes; the lazy pattern is ``next(gen,
    default)`` or a counted pull.
  - Late binding in loops: ``(lambda: i for i in range(3))`` captures
    the *variable*, not the value — every lambda returns 2. In a
    pipeline this shows up as every stage using the last config.

Your solution: ``streaming_total(gen, key)`` — sums ``float(item[key])``
over a generator of dicts, skipping items whose value is missing or
not numeric, and returns ``(total, count, skipped)``. It must work on
an *infinite* source (test will ``islice`` it) — if your function
materializes anything, the test hangs.

Plain words: the cashier counts bills as they pass under the scanner —
the drawer never holds the whole day's cash at once.

ANALOGY
-------
A turnstile vs. a headcount list: the turnstile counts people as they
walk through; nobody needs a roster of everyone who ever entered.

YOUR TASK
---------
Implement ``streaming_total`` below. Then run the tests:
``python -m pytest tests -q`` from the day-06 folder.
"""


def streaming_total(gen, key):
    """Sum float(item[key]) over generator *gen* without materializing it.

    Skips items where the key is missing or not numeric.
    Returns (total, count, skipped).
    """
    total = 0.0
    count = 0
    skipped = 0
    for item in gen:
        raw = item.get(key) if isinstance(item, dict) else None
        try:
            total += float(raw)
        except (TypeError, ValueError):
            skipped += 1
            continue
        count += 1
    return total, count, skipped


if __name__ == "__main__":
    from itertools import islice, count

    # An endless "file" of rows — impossible to load, trivial to stream:
    endless = ({"amt": str(i % 7), "ok": True} for i in count())
    total, n, skipped = streaming_total(islice(endless, 1_000_000), "amt")
    print(total, n, skipped)  # 2999997.0 1000000 0 — one pass, flat memory

    messy = ({"amt": v} for v in ["1.5", "N/A", None, "2.5"])
    print(streaming_total(messy, "amt"))  # (4.0, 2, 2)
