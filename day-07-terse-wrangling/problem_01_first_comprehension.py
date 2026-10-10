"""Problem 1 — The one-line transform
=================================

THE PROBLEM (beginner foothold first)
------------------------------------
Every pipeline starts the same way: take a pile of raw records, keep the
good ones, reshape them. The first-draft version looks like this:

    clean = []
    for email in raw_emails:
        email = email.strip().lower()
        if email:
            clean.append(email)

Three ideas (loop, filter, transform) spread over six lines. A list
comprehension says the same thing in one pass:

    clean = [e.strip().lower() for e in raw_emails if e.strip()]

Read it left to right: TRANSFORM for ITEM in SOURCE if CONDITION.
The brackets build a list; the expression up front is the reshape;
the ``if`` at the end is the filter. ``if`` runs first per item, so a
row that fails the filter never gets transformed.

Plain words: the loop version is a recipe with six steps. The
comprehension is the same recipe written as one sentence.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Comprehensions are EAGER: ``[x for x in ten_million_rows]`` builds
    the whole list in memory. If you only needed to iterate once,
    you wanted ``(x for x in rows)`` — parentheses stream, brackets
    build (see problem 5).
  - The filter runs before the transform, so ``[int(x) for x in vals
    if x.isdigit()]`` is safe but ``[x for x in vals if int(x) > 0]``
    re-parses on every check. Hoist expensive work out.
  - A comprehension with three ``for``s and two ``if``s is no longer
    terse — it is a puzzle. Split it back into a loop.

Your solution: ``clean_emails(rows)`` — strip + lowercase every entry,
dropping empties/whitespace-only ones. And ``big_amounts(rows,
minimum)`` — the amounts at or above ``minimum``, via one
comprehension with an ``if`` filter.

Plain words: one line that says "reshape these, keep those".

ANALOGY
-------
A coffee filter vs. picking grounds out by hand: the comprehension is
the filter — pour everything in, the shape decides what comes through.

YOUR TASK
---------
Implement ``clean_emails`` and ``big_amounts`` below. Then run the
tests: ``python -m pytest tests -q`` from the day-07 folder.
"""


def clean_emails(rows):
    """Strip + lowercase every entry; drop empties, blanks, and non-strings."""
    return [e.strip().lower() for e in rows
            if isinstance(e, str) and e.strip()]


def big_amounts(rows, minimum):
    """Return the amounts at or above *minimum*, in original order."""
    return [r["amt"] for r in rows if r["amt"] >= minimum]


if __name__ == "__main__":
    raw = ["  Ada@Mail.com ", "", "   ", "bob@mail.com", "ADA@mail.com"]
    print(clean_emails(raw))       # ['ada@mail.com', 'bob@mail.com', 'ada@mail.com']
    txns = [{"amt": 5}, {"amt": 500}, {"amt": 50}]
    print(big_amounts(txns, 50))   # [500, 50]
