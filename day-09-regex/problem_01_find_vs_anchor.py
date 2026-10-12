"""Problem 1 — Find anywhere vs. pinned to the start
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Error codes hide inside long log lines, never at the start:

    "2026-10-12 09:14:02 svc=auth request_id=abc-123 ERROR-5042 upstream timeout"

``re.match("ERROR-(\\d+)", line)`` returns None — match asks "does the
line BEGIN with this?". ``re.search`` asks "is it anywhere in the line?".
Logs rarely start where you think, so searching is the default; anchoring
is a deliberate choice, not an accident.

Plain words: match checks the front door; search checks the whole house.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - match() is not "broken search" — anchored matching is exactly what
    you want when VALIDATING a whole line (``^(\\d{4}-\\d{2}-\\d{2})$``).
    The bug is using the wrong one for the job.
  - Case drift: some services log "error-5042". Decide your case policy
    once (re.IGNORECASE vs. normalized input) instead of sprinkling flags.
  - A None match that you .group() without checking becomes an
    AttributeError three frames downstream — check before you extract.

Your solution: ``find_error_code(line)`` — return the numeric code as an
``int`` (e.g. 5042) for the first "ERROR-<digits>" anywhere in the line,
case-insensitive. Return ``None`` when there is no error code.

Plain words: find it wherever it hides; say None honestly when it's absent.

ANALOGY
-------
match() is checking whether the line *starts with* your name on a name
tag; search() is scanning the whole room for you.

YOUR TASK
---------
Implement ``find_error_code`` below. Then run the tests:
``python -m pytest tests -q`` from the day-09 folder.
"""

import re

_ERROR = re.compile(r"error-(\d+)", re.IGNORECASE)


def find_error_code(line):
    """Return the first ERROR-<digits> code as int, or None."""
    if not isinstance(line, str):
        return None
    m = _ERROR.search(line)
    return int(m.group(1)) if m else None


if __name__ == "__main__":
    print(find_error_code("2026-10-12 09:14:02 svc=auth ERROR-5042 upstream timeout"))
    print(find_error_code("all clear, nothing to see"))
