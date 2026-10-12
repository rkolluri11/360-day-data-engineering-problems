"""Problem 2 — Named groups: fields out of a messy log line
========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Log lines carry fields, not prose:

    "2026-10-12 09:14:02 ERROR [auth] login failed for user jdoe"

``(?P<level>ERROR)`` names what you capture. Downstream code reads
``m["level"]`` instead of ``m.group(3)`` — and when someone adds a field
in the middle six months from now, nothing downstream shifts.

Plain words: named groups are column headers for your regex.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Real logs drift: the service tag ``[auth]`` is sometimes missing, and
    the timestamp sometimes carries a ``Z``. One pattern must handle
    every shape the fleet actually emits — make optional parts optional
    (``(...)?``), never write three patterns.
  - Greedy ``.*`` for the message would be fine here ONLY because it is
    last. A greedy group in the middle swallows your delimiters (rung 3).
  - A line that matches nothing must come back as ``None`` — not a dict
    of Nones. "No match" and "matched with blanks" are different answers.

Your solution: ``parse_log_line(line)`` — return a dict with keys
``ts``, ``level``, ``service`` (None when the ``[tag]`` is absent), and
``msg``. ``ts`` keeps the raw timestamp string. Return ``None`` when the
line doesn't match at all.

Plain words: one reader for every log shape the fleet emits.

ANALOGY
-------
Named groups are labeled jars on a shelf; positional groups are identical
jars you have to open to identify.

YOUR TASK
---------
Implement ``parse_log_line`` below. Then run the tests:
``python -m pytest tests -q`` from the day-09 folder.
"""

import re

_LOG = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}Z?)\s+"
    r"(?P<level>INFO|WARN|ERROR)\s+"
    r"(?:\[(?P<service>[^\]]+)\]\s+)?"
    r"(?P<msg>.*)"
)


def parse_log_line(line):
    """Parse a log line into named fields; None when it doesn't match."""
    if not isinstance(line, str):
        return None
    m = _LOG.match(line.strip())
    if not m:
        return None
    return {
        "ts": m["ts"],
        "level": m["level"],
        "service": m["service"],   # None when the [tag] is absent
        "msg": m["msg"],
    }


if __name__ == "__main__":
    print(parse_log_line("2026-10-12 09:14:02 ERROR [auth] login failed for user jdoe"))
    print(parse_log_line("2026-10-12T09:14:02Z WARN disk at 91%"))
    print(parse_log_line("not a log line at all"))
