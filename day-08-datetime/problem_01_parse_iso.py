"""Problem 1 — Parse the ISO string
===============================

THE PROBLEM (beginner foothold first)
------------------------------------
Raw events arrive as strings: "2026-10-11T09:00:00", "2026-10-11T09:00:00Z",
"2026-10-11T09:00:00+05:30". The first-draft version hand-slices them:

    date_part = s.split("T")[0]          # breaks on "Z", on offsets, on space separators

``datetime.fromisoformat`` reads the whole ISO-8601 shape for you — date,
time, fractional seconds, offsets, and (on Python 3.11+) the "Z" suffix.
Read it left to right: FROM ISO FORMAT — the string already carries the
structure; you are just decoding it.

Plain words: don't carve the timestamp with a knife when the standard
library hands you the can opener.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Python < 3.11's ``fromisoformat`` chokes on "Z". Pipelines that run
    on mixed versions need the explicit "Z" -> "+00:00" fallback below.
  - ``fromisoformat`` returns a NAIVE datetime when the string has no
    offset — "2026-10-11T09:00:00" parses fine and tells you nothing
    about whose 9 AM it is. Parsing is rung 1; awareness is rung 2.
  - Garbage in must fail LOUD: a silent ``None`` on bad input becomes a
    midnight timestamp three jobs downstream. Raise ValueError here.

Your solution: ``parse_timestamp(s)`` — return a ``datetime`` for any
ISO-8601 string (plain, "Z", or offset). Raise ``ValueError`` on
anything else, including empty/whitespace strings.

Plain words: one reader for every timestamp shape, and it shouts on garbage.

ANALOGY
-------
A barcode scanner vs. reading the digits by eye: the standard shape is
machine-readable for a reason — let the machine read it.

YOUR TASK
---------
Implement ``parse_timestamp`` below. Then run the tests:
``python -m pytest tests -q`` from the day-08 folder.
"""

from datetime import datetime


def parse_timestamp(s):
    """Parse an ISO-8601 string into a datetime; raise ValueError on garbage."""
    if not isinstance(s, str) or not s.strip():
        raise ValueError("expected an ISO-8601 string, got %r" % (s,))
    text = s.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    # "Z" suffix: native on 3.11+, spelled out here for older runtimes
    if text.endswith(("Z", "z")):
        return datetime.fromisoformat(text[:-1] + "+00:00")
    raise ValueError("not an ISO-8601 timestamp: %r" % (s,))


if __name__ == "__main__":
    print(parse_timestamp("2026-10-11T09:00:00"))        # naive: 2026-10-11 09:00:00
    print(parse_timestamp("2026-10-11T09:00:00Z"))       # aware: +00:00
    print(parse_timestamp("2026-10-11T14:30:00+05:30"))  # aware: +05:30
