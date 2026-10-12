"""Problem 4 — Compile once, write it like real code
================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A one-line monster nobody can read at 2 AM:

    r"(\\d+\\.\\d+\\.\\d+\\.\\d+)\\s+-\\s+(\\d{3})\\s+(GET|POST)\\s+(\\S+)"

``re.VERBOSE`` lets the pattern span lines with comments, and compiling
once at module level means the engine builds it a single time instead of
once per log line. Readable and fast are the same change.

Plain words: write the pattern like code, because it IS code.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``re.compile`` inside a loop (or inside the function called per line)
    re-parses the pattern every call. Python caches the last 512, but
    "cached" is not "free" — hoist it to module level.
  - VERBOSE mode treats unescaped whitespace and ``#`` as formatting —
    literal spaces must be ``\\ `` or ``\\s``, and a literal ``#`` must be
    escaped. The classic VERBOSE bug is a pattern that "stopped matching"
    after reformatting.
  - Return a dict with named fields, not a tuple — positional fields are
    rung-2's lesson all over again.

Your solution: ``parse_access_log(line)`` — parse an access-log line
``"203.0.113.7 - 200 GET /api/events"`` into ``{"ip", "code", "method",
"path"}`` (code as int). Use a module-level ``re.compile`` with
``re.VERBOSE`` and named groups. Return ``None`` on no match.

Plain words: one compiled, commented pattern; structured fields out.

ANALOGY
-------
A VERBOSE pattern is a recipe with the steps written out; a one-liner is
the same recipe as a single run-on sentence.

YOUR TASK
---------
Implement ``parse_access_log`` below. Then run the tests:
``python -m pytest tests -q`` from the day-09 folder.
"""

import re

_ACCESS = re.compile(
    r"""
    (?P<ip>\d+\.\d+\.\d+\.\d+)   # source host (IPv4)
    \s+-\s+                      # literal separator, spaces included
    (?P<code>\d{3})              # status code
    \s+
    (?P<method>GET|POST|PUT|DELETE|PATCH|HEAD)  # HTTP verb
    \s+
    (?P<path>\S+)                # request path, no spaces allowed
    """,
    re.VERBOSE,
)


def parse_access_log(line):
    """Parse an access-log line into named fields; None on no match."""
    if not isinstance(line, str):
        return None
    m = _ACCESS.match(line.strip())
    if not m:
        return None
    return {
        "ip": m["ip"],
        "code": int(m["code"]),
        "method": m["method"],
        "path": m["path"],
    }


if __name__ == "__main__":
    print(parse_access_log("203.0.113.7 - 200 GET /api/events"))
    print(parse_access_log("10.0.0.9 - 500 POST /api/ingest"))
    print(parse_access_log("garbage in"))
