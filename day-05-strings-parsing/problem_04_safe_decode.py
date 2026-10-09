"""Problem 4 — The bytes that lied about being text
==================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A file arrives as bytes:

    b"caf\xc3\xa9"   # "café" in UTF-8

``raw.decode("utf-8")`` gives ``"café"``. But decode those same bytes
as latin-1 and you get ``"cafÃ©"`` — mojibake. Worse: one file in a
batch decoded with the wrong codec poisons a whole column, and
``UnicodeDecodeError`` on a single bad byte can kill a 2M-row load.

Plain words: bytes don't know what language they're in. Decoding is a
guess, and a wrong guess doesn't always raise — sometimes it just
lies quietly.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A nightly vendor feed mixes encodings across files — and occasionally
*within* one file:
  - most files are UTF-8, but legacy ones are windows-1252/latin-1
  - a single 0xFF byte mid-file raises UnicodeDecodeError and aborts
    the whole batch under a naive ``decode("utf-8")``
  - double-encoded text (UTF-8 bytes decoded as latin-1, then
    re-encoded) shows up as ``"cafÃ©"`` — valid Unicode, wrong text

Your solution:
  - ``safe_decode(raw, encoding="utf-8")`` — decodes, replacing
    undecodable bytes with U+FFFD instead of raising, so one bad byte
    never kills a batch. Returns ``str`` always.
  - ``looks_mojibake(s)`` — heuristic ``True`` when text shows the
    classic double-encoding signature: characters like Ã, Â, €, or
    sequences such as "Ã©" / "Â" that appear when UTF-8 bytes were read
    as latin-1. (Heuristic, not proof — flag for a human, don't
    auto-"fix".)

Plain words: wear a seatbelt (replace, don't crash) and keep a
smoke detector (the heuristic) — you investigate the alarm, you
don't let it rewire the house.

ANALOGY
-------
Reading a French menu as if it were English: most words look
plausible, a few are absurd — and you only notice if you're
looking for it.

YOUR TASK
---------
Implement ``safe_decode`` and ``looks_mojibake`` below. Then run:
``python -m pytest tests -q`` from the day-05 folder.
"""

# Signatures of UTF-8 bytes misread as latin-1 / windows-1252.
_MOJIBAKE_MARKS = ("Ã", "Â", "â", "€", "œ", "æ")


def safe_decode(raw, encoding="utf-8"):
    """Decode bytes to str, replacing bad bytes instead of raising.

    Accepts bytes/bytearray; passes str through unchanged. Always
    returns str — one corrupt byte never kills the batch.
    """
    if isinstance(raw, str):
        return raw
    return bytes(raw).decode(encoding, errors="replace")


def looks_mojibake(s):
    """Heuristic: True if *s* looks double-encoded (UTF-8 read as latin-1).

    Flags the classic signatures (Ã©, Â, â€...) so a human can check.
    Not proof — never auto-repair on this signal alone.
    """
    if not s:
        return False
    return any(mark in s for mark in _MOJIBAKE_MARKS)


if __name__ == "__main__":
    print(repr(safe_decode(b"caf\xc3\xa9")))          # café
    print(repr(safe_decode(b"caf\xc3\xa9", "latin-1")))  # cafÃ© — lies quietly
    print(repr(safe_decode(b"ok\xffbad")))           # no crash: ok�bad
    print(looks_mojibake("cafÃ©"), looks_mojibake("café"))
