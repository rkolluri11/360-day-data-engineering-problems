"""Day 20 - Problem 1: the JSON roundtrip, and what it quietly changes.

THE PROBLEM (beginner foothold first)
------------------------------------
JSON is the default format for APIs, logs, and configs — because
every language reads it and every human can debug it. But JSON
only knows six kinds of values: objects, arrays, strings,
numbers, booleans, and null. Everything else gets coerced:

    >>> import json
    >>> json.dumps({"when": "2026-10-23"})   # a date is just a string now
    >>> json.loads('{"n": 19.0}')            # ints can come back as floats

If you dump a Python dict and load it back, the VALUES look the
same — but the TYPES may have silently changed.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Dates, datetimes, decimals, and tuples do not survive a
    JSON roundtrip as themselves: datetimes need a custom
    encoder (usually ISO strings), tuples come back as lists,
    and Decimals either error or become floats.
  - ``1e400`` and NaN are not valid JSON — Python writes them
    anyway (``NaN``, ``Infinity``), and strict parsers in other
    languages reject them.
  - A float like 19.99 round-trips fine, but ``0.1 + 0.2`` does
    not equal ``0.3`` in ANY format — the drift is JSON making
    it visible, not causing it.
  - The real trap: ``json.loads`` never fails on type drift, so
    a field that changed from ``19.99`` to ``"19.99"`` upstream
    silently breaks a downstream join.

Your solution: ``json_roundtrip`` and ``json_type_report``
are already written. The tests prove values survive while
types shift — and that the report names every shift.

ANALOGY
-------
JSON is the labeled cardboard box: anyone can open it, but the
contents get repackaged in transit. Check the labels when it
arrives, not when you unpack it at midnight.
"""
import json


def json_roundtrip(record):
    """Dump ``record`` to JSON and parse it back. Returns the parsed dict."""
    return json.loads(json.dumps(record))


def json_type_report(record):
    """Return {key: (type_before, type_after)} for a JSON roundtrip.

    Only JSON-native records (dicts, lists, str, int, float, bool,
    None) are supported — that is the point: anything else must be
    encoded by the caller first.
    """
    before = {k: type(v).__name__ for k, v in record.items()}
    after = {k: type(v).__name__ for k, v in json_roundtrip(record).items()}
    return {k: (before[k], after[k]) for k in record}


if __name__ == "__main__":
    record = {"user_id": "u-7", "amount": 19.99, "tags": ("a", "b"), "n": 3}
    print("roundtrip:", json_roundtrip(record))
    for key, (b, a) in json_type_report(record).items():
        flag = "" if b == a else "   <-- TYPE SHIFT"
        print(f"{key}: {b} -> {a}{flag}")
