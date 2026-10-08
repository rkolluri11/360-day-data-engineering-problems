"""Problem 13 — The validators that all checked the wrong column
=============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You build one checker per column in a loop:

    checkers = []
    for col in ["age", "email", "zip"]:
        checkers.append(lambda row: row[col] is not None)

Every checker raises ``NameError``... or worse, if ``col`` still
exists afterward, ALL THREE checkers validate the same column —
whichever value ``col`` held when the loop ENDED. Python closures
capture the *variable*, not its value at creation time.

Plain words: each checker holds a sticky note saying "look at the
column named on the whiteboard" — but there's one whiteboard, and
the loop keeps erasing and rewriting it. When the checkers finally
run, they all read whatever was written last.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A config-driven ETL builds per-column quality checks from YAML:

    columns:
      - name: amount
        rule: positive
      - name: currency
        rule: not_null
      - name: event_ts
        rule: not_null

The builder loop creates one closure per column. Because of
late binding, every check validates ``event_ts`` — the last column.
Result: negative amounts sail through to the revenue table for two
weeks, and nobody is alerted because "all checks passed."

Your solution: ``make_check(column, rule)`` — a factory function.
Each call gets its OWN parameter binding, so each returned closure
remembers its own column forever. The loop just calls the factory;
no closure ever shares the loop variable again.

Plain words: instead of one shared whiteboard, the factory hands
each checker its own printed card with the column name on it. The
loop can scribble whatever it wants afterward — the cards never
change.

ANALOGY
-------
Name tags at a conference vs. one shared "HELLO MY NAME IS" board.
If everyone points at the same board, every photo caption names the
last person who wrote on it. Printed name tags travel with each
person — correct forever, whatever the board says later.
"""

from __future__ import annotations


def make_check(column, rule):
    """Build a row-checker bound to ONE column and ONE rule.

    The factory's parameters are fresh on every call, so the closure
    captures its own private copies — never the loop variable.
    """
    if rule == "not_null":
        def check(row, _col=column):
            # Plain words: fail the row if this column is missing/null.
            return row.get(_col) is not None
    elif rule == "positive":
        def check(row, _col=column):
            # Plain words: fail unless this column holds a number > 0.
            value = row.get(_col)
            return isinstance(value, (int, float)) and value > 0
    else:
        raise ValueError(f"unknown rule: {rule!r}")
    check.__name__ = f"check_{column}_{rule}"
    return check


def build_checks(specs):
    """Build one checker per column spec: [{"name":..,"rule":..}, ...].

    Each spec goes through the factory, so late binding can never
    make every checker validate the last column.
    """
    return [make_check(spec["name"], spec["rule"]) for spec in specs]


def validate(rows, checks):
    """Split rows into (good, bad); bad rows list the failing checks."""
    good, bad = [], []
    for row in rows:
        failed = [c.__name__ for c in checks if not c(row)]
        (good if not failed else bad).append(
            row if not failed else {**row, "_failed": failed})
    return good, bad


if __name__ == "__main__":
    specs = [
        {"name": "amount", "rule": "positive"},
        {"name": "currency", "rule": "not_null"},
        {"name": "event_ts", "rule": "not_null"},
    ]
    checks = build_checks(specs)

    rows = [
        {"amount": 100, "currency": "USD", "event_ts": "2026-10-06"},
        {"amount": -5, "currency": "USD", "event_ts": "2026-10-06"},
        {"amount": 20, "currency": None, "event_ts": "2026-10-06"},
    ]
    good, bad = validate(rows, checks)
    print("good:", len(good))  # 1
    print("bad:", len(bad))    # 2 — negative amount caught, null caught
    for b in bad:
        print(b["_failed"])
