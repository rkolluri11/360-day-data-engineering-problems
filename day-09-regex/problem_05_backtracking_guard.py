"""Problem 5 — Defuse the backtracking time bomb
==============================================

THE PROBLEM (beginner foothold first)
------------------------------------
A validation pattern with nested quantifiers:

    ^(\\w+\\s?)+$          # DANGEROUS — never use this

On one malformed 200-character line, the engine re-splits the same
characters millions of ways trying to make the pattern fit: exponential
backtracking. One line, 40 minutes of CPU, SLA blown.

The fix is 10 seconds: ``^[\\w\\s]+$`` — one flat character class, no
nesting, no explosion. Same accepted language, linear time.

Plain words: nested quantifiers are a knotted sieve — they clog the line.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Flattening isn't always possible (some patterns NEED alternation).
    The second guard is a LENGTH CAP: refuse to run an expensive pattern
    on input longer than N characters before the engine ever sees it.
  - Never "fix" backtracking by adding ``re`` timeouts — the stdlib has
    none. Guard the input, not the clock.
  - ``\\w`` matches ``[a-zA-Z0-9_]`` — know exactly what your class
    admits, or attackers will find the gap for you.

Your solution: ``validate_token(line)`` — return True when the line is a
safe token: at most 200 characters AND fully matched by the flat pattern
``^[\\w\\s]+$``. Anything else (too long, bad characters, non-string)
returns False. Must complete instantly even on adversarial input.

Plain words: flat pattern + length guard = a validator that can't hang.

ANALOGY
-------
The length guard is the bouncer checking ID at the door so the knotted
sieve never gets a crowd big enough to clog.

YOUR TASK
---------
Implement ``validate_token`` below. Then run the tests:
``python -m pytest tests -q`` from the day-09 folder.
"""

import re

_MAX_LEN = 200
_SAFE = re.compile(r"^[\w\s]+$")          # flat: one class, linear time
# _DANGEROUS = re.compile(r"^(\w+\s?)+$")  # nested quantifiers — hangs


def validate_token(line):
    """True for a safe token (<=200 chars, flat-pattern match), else False."""
    if not isinstance(line, str):
        return False
    if len(line) > _MAX_LEN:      # length guard runs before the engine
        return False
    return _SAFE.match(line) is not None


if __name__ == "__main__":
    print(validate_token("batch 42 ok"))            # True
    print(validate_token("batch-42!"))              # False: bad characters
    print(validate_token("!" * 200))                # False, and instant
    print(validate_token("a" * 201))                # False: over the cap
