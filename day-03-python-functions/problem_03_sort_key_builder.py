"""Problem 3 — The sort key that died on one bad row
===============================================

THE PROBLEM (beginner foothold first)
------------------------------------
Sort events by timestamp:

    events.sort(key=lambda row: row["ts"])

One row in 10 million has no ``"ts"`` key. At 3 AM the whole sort —
and the pipeline — dies with ``KeyError``. The lambda assumed every
row looks like the first hundred.

Plain words: a bouncer who only knows one ID format turns away the
whole line when one guest shows a passport.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
You sort messy JSON logs for a merge step. Real rows look like:

    {"ts": 169, "user": "a"}        # ints
    {"ts": "2024-01-01", "user": "b"}  # strings sneak in
    {"user": "c"}                   # missing key
    {"ts": None, "user": "d"}       # explicit null

``sorted(rows, key=lambda r: r["ts"])`` raises ``KeyError`` on the
third row and ``TypeError`` (can't compare int and str) on the
second. Your solution: ``sort_key(*fields, desc=())`` — a
*higher-order function* that builds and returns a key function:

  - missing keys and ``None`` sort LAST (ascending), never raise;
  - mixed types never raise: values are normalized to
    ``(type_rank, value)`` tuples that always compare cleanly
    (numbers < strings < everything else, by ``repr``);
  - per-field descending via ``desc=("ts",)`` — other fields stay
    ascending. (``sorted(reverse=True)`` flips *everything*; you
    need per-column direction like a real ORDER BY.)
  - works for multi-field ordering: ``sort_key("region", "ts")``.

Plain words: give the bouncer a rulebook that covers every ID
format, sends the unclear cases to the back of the line, and lets
each column face its own direction.

ANALOGY
-------
Airport boarding: passengers are ordered by group, then seat. A
missing boarding pass doesn't cancel the flight — that passenger
boards last. And first-class boards front-to-back while economy
boards back-to-front: each group has its own direction, one
announcement.
"""

from __future__ import annotations


class _Desc:
    """Wrap a normalized key so it sorts in reverse."""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self.value > other.value

    def __le__(self, other):
        return self.value >= other.value

    def __gt__(self, other):
        return self.value < other.value

    def __ge__(self, other):
        return self.value <= other.value

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"_Desc({self.value!r})"


def _normalize(value):
    """Map any value to a tuple that always compares cleanly.

    Rank 0: numbers (bools ride along — they are ints in Python).
    Rank 1: strings. Rank 2: everything else, compared by repr.
    Rank 3: missing/None — always the highest rank, so it sorts
    LAST ascending (and first descending, like SQL's NULLS FIRST).
    Within a rank, the third element is always the same type, so
    tuples never hit an unorderable comparison.
    """
    if value is None:
        return (3, 0, "")
    if isinstance(value, (int, float)):
        return (0, 0, float(value))
    if isinstance(value, str):
        return (1, 0, value)
    return (2, 0, repr(value))


def _rank(value, descending):
    norm = _normalize(value)
    return _Desc(norm) if descending else norm


def sort_key(*fields, desc=()):
    """Build a sort key function for messy rows.

    ``sorted(rows, key=sort_key("region", "ts", desc=("ts",)))``
    orders by region ascending, then ts descending, without ever
    raising on missing keys, None, or mixed types.
    """
    if not fields:
        raise ValueError("sort_key needs at least one field")
    desc_set = set(desc)
    unknown = desc_set - set(fields)
    if unknown:
        raise ValueError(f"desc lists unknown field(s): {sorted(unknown)}")

    def key(row):
        get = row.get if isinstance(row, dict) else None
        parts = []
        for field in fields:
            value = get(field) if get else getattr(row, field, None)
            parts.append(_rank(value, field in desc_set))
        return tuple(parts)

    return key


if __name__ == "__main__":
    rows = [
        {"ts": 169, "user": "a"},
        {"ts": "2024-01-01", "user": "b"},
        {"user": "c"},
        {"ts": None, "user": "d"},
        {"ts": 42, "user": "e"},
    ]
    for row in sorted(rows, key=sort_key("ts")):
        print(row)
    print("--- ts desc ---")
    for row in sorted(rows, key=sort_key("ts", desc=("ts",))):
        print(row["user"], "->", row.get("ts"))
