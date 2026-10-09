"""Problem 3 — The clean field that wasn't
========================================

THE PROBLEM (beginner foothold first)
------------------------------------
A field arrives "clean":

    "  Alice   "

``s.strip()`` handles the spaces. But some dirt is invisible:

    "Alice\\u200b"   # zero-width space — you can't see it,
                     # but "Alice\\u200b" != "Alice"

Joins fail. Dedup counts double. The dashboard shows two "Alices".

Plain words: Unicode has characters with no visible glyph — zero-width
spaces, byte-order marks, soft hyphens. ``strip()`` only removes
characters it knows are whitespace; these aren't on its list.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Copy-pasted data from web forms, PDFs, and chat apps arrives with:
  - U+200B ZERO WIDTH SPACE, U+200C/D joiners — invisible, break equality
  - U+FEFF BYTE ORDER MARK — hides at the start of the first column
  - U+00AD SOFT HYPHEN — invisible until a line break, then "­" appears
  - non-breaking spaces (U+00A0) — ``strip()`` won't remove these, and
    ``"a\\u00a0b".split(" ")`` won't split on them
  - runs of mixed whitespace (tabs, newlines) inside free text

Your solution: ``clean_text(s)`` that:
  - deletes the known invisible characters outright,
  - converts non-breaking spaces to regular spaces,
  - collapses every run of whitespace to a single space,
  - strips leading/trailing whitespace,
  - never raises on empty/whitespace-only input (returns "").

Plain words: run every field through a metal detector before it enters
the building — invisible metal still sets it off.

ANALOGY
-------
Proofreading with "show invisibles" on: the document looks identical,
but now you can see every hidden tab, double space, and stray mark.

YOUR TASK
---------
Implement ``clean_text`` below. Then run:
``python -m pytest tests -q`` from the day-05 folder.
"""

import re
import unicodedata

# Characters that are invisible but break equality / joins / dedup.
INVISIBLE = {
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\ufeff",  # BYTE ORDER MARK
    "\u00ad",  # SOFT HYPHEN
    "\u2060",  # WORD JOINER
}

_WS_RUN = re.compile(r"\s+")


def clean_text(s):
    """Remove invisible characters and normalize all whitespace.

    Returns "" for empty or whitespace-only input. Never raises.
    """
    if not s:
        return ""
    # 1. delete known invisible characters
    for ch in INVISIBLE:
        s = s.replace(ch, "")
    # 2. non-breaking space -> regular space (strip/split miss U+00A0)
    s = s.replace("\u00a0", " ")
    # 3. drop any other format/control characters (category Cf/Cc),
    #    keeping the whitespace we are about to normalize
    s = "".join(
        ch for ch in s
        if ch.isspace() or unicodedata.category(ch) not in ("Cf", "Cc")
    )
    # 4. collapse whitespace runs, strip ends
    return _WS_RUN.sub(" ", s).strip()


if __name__ == "__main__":
    print(repr(clean_text("  Alice\u200b  ")))
    print(repr(clean_text("\ufeffORD-42\u00a0")))
    print(repr(clean_text("a\t\tb\n c")))
    print(repr(clean_text("   ")))
