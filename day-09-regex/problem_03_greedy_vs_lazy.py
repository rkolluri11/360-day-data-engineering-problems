"""Problem 3 — Greedy vs. lazy: the bracket trap
==============================================

THE PROBLEM (beginner foothold first)
------------------------------------
Extract the first ``[...]`` tag from a line:

    "tags: [ingest] stage [parse] failed"

``r"\\[(.*)\\]"`` returns ``ingest] stage [parse`` — greedy ``.*`` eats
from the FIRST ``[`` to the LAST ``]``. Lazy ``.*?`` stops at the first
``]`` and returns ``ingest``. Greedy is the default, and it lies.

Plain words: greedy grabs the whole buffet; lazy takes one plate.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Even lazier: ``[^\\]]*`` (a negated class) beats ``.*?`` — it cannot
    overshoot by construction, and it runs faster. Prefer character
    classes over dot-star whenever the delimiter is known.
  - Nested brackets (``[a [b] c]``) are NOT regex's job. A regex will
    silently give you the wrong answer; detect nesting and fail loud or
    hand it to a real parser.
  - Lines with no brackets at all must return ``None``, not crash.

Your solution: ``first_bracketed(line)`` — return the content of the
FIRST ``[...]`` group, or ``None`` when there is none. If the content
itself contains a bracket (nesting), raise ``ValueError`` — never guess.

Plain words: take the first tag, exactly; refuse to guess at nesting.

ANALOGY
-------
Greedy is pouring the whole cereal box; lazy is one measured scoop; a
negated class is a scoop with a lid.

YOUR TASK
---------
Implement ``first_bracketed`` below. Then run the tests:
``python -m pytest tests -q`` from the day-09 folder.
"""

import re

_FIRST_TAG = re.compile(r"\[([^\]]*)\]")


def first_bracketed(line):
    """Return the first [...] content, or None; ValueError on nesting."""
    if not isinstance(line, str):
        return None
    m = _FIRST_TAG.search(line)
    if not m:
        return None
    content = m.group(1)
    if "[" in content:
        raise ValueError("nested brackets are not regex's job: %r" % (line,))
    return content


if __name__ == "__main__":
    print(first_bracketed("tags: [ingest] stage [parse] failed"))  # ingest
    print(first_bracketed("nothing bracketed here"))              # None
