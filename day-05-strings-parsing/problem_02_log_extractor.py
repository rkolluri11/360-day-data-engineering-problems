"""Problem 2 — The log line with three faces
==========================================

THE PROBLEM (beginner foothold first)
------------------------------------
A log line looks like this:

    2026-10-08 07:12:44 [ERROR] disk full on /data

You need the timestamp, the level, and the message — separately. The
temptation is ``line.split()``, but the message itself contains spaces,
so ``parts[2]`` is ``[ERROR]`` today and something else tomorrow.

Plain words: the line has *structure* (fixed-shape head) followed by
*free text* (the message). Split the head with a pattern; leave the
tail alone.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Real logs are feral:
  - some lines lack the level: ``2026-10-08 07:12:44 heartbeat ok``
  - some lack everything: ``--- rotated at midnight ---``
  - levels vary: ``[ERROR]``, ``[WARN]``, ``[INFO]``, ``[DEBUG]``
  - you must scan 10M lines and count ERRORs — regex on every line is
    correct but slow; a fast pre-filter matters.

Your solution:
  - ``parse_log_line(line)`` → ``{"ts": ..., "level": ..., "msg": ...}``
    or ``None`` when the line has no recognizable head. Uses one
    compiled regex (compiled ONCE at import — never recompile per line).
  - ``is_error_line(line)`` → bool, using only cheap ``str`` methods
    (``in`` / ``startswith``) as a pre-filter before the regex runs.

Plain words: the bouncer checks the guest list (regex) only after the
doorman (``in``) waves the line through — 10M lines, no wasted work.

ANALOGY
-------
Airport security: the fast lane (str methods) clears obvious cases;
only the flagged bags go through the scanner (regex).

YOUR TASK
---------
Implement ``parse_log_line`` and ``is_error_line`` below. Then run:
``python -m pytest tests -q`` from the day-05 folder.
"""

import re

LOG_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"  # 2026-10-08 07:12:44
    r"(?:\s+\[(?P<level>[A-Z]+)\])?"                # optional [LEVEL]
    r"\s*(?P<msg>.*)$"                             # the rest is message
)


def parse_log_line(line):
    """Parse a log line into {"ts", "level", "msg"}; None if no head."""
    m = LOG_RE.match(line)
    if not m:
        return None
    return {
        "ts": m.group("ts"),
        "level": m.group("level"),  # None when absent
        "msg": m.group("msg").strip(),
    }


def is_error_line(line):
    """Fast pre-filter: True if the line looks like an ERROR line.

    Uses only str methods — no regex. Call this before parse_log_line
    when scanning millions of lines.
    """
    return "[ERROR]" in line


if __name__ == "__main__":
    print(parse_log_line("2026-10-08 07:12:44 [ERROR] disk full on /data"))
    print(parse_log_line("2026-10-08 07:12:44 heartbeat ok"))
    print(parse_log_line("--- rotated at midnight ---"))
    print(is_error_line("2026-10-08 07:12:44 [ERROR] boom"))
