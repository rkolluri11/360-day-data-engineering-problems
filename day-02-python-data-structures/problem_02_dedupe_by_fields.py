"""Problem 2 — The dedup keys that wouldn't freeze
=================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Events arrive as dicts, and two events are duplicates when a few
fields match:

    {"event_id": "e1", "source": "web", "ts": 12}
    {"event_id": "e1", "source": "web", "ts": 19}   # same e1+web: duplicate

Write ``dedupe_by_fields(records, fields)`` that returns the records
with duplicates removed (first occurrence kept), where a duplicate
means "same values for every field in ``fields``".

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Dicts can't go into a set — they're unhashable. So a dedup key built
as a plain tuple of field values explodes the moment one value is a
list, a dict, or a set (think ``tags: ["click", "signup"]`` inside the
event). Your key builder must *freeze* any value recursively —
lists to tuples, dicts to sorted key/value tuples, sets to
frozensets — so the key is always hashable, no matter what the
pipeline throws at it. Records missing a field count as ``None`` for
that field.

Plain words: before asking the magic bag "seen this?", turn the
wobbly jelly of a dict into a frozen ice cube — same shape, now
solid enough to hold.

ANALOGY
-------
You can't file a liquid. Pour the soup into an ice-cube tray, freeze
it, and now every portion stacks neatly in the freezer drawer — same
soup, fileable shape.
"""

from __future__ import annotations


def _freeze(value):
    """Recursively convert a value into a hashable, canonical form."""
    if isinstance(value, dict):
        # Sort by repr of the key so mixed-type keys can't break ordering.
        return tuple(
            (key, _freeze(val))
            for key, val in sorted(value.items(), key=lambda kv: repr(kv[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def dedupe_by_fields(records, fields):
    """Dedupe dicts by ``fields``, keeping the first occurrence of each key.

    The dedup key is a frozen tuple of the field values, so unhashable
    values (lists, dicts, sets) work. Missing fields count as None.
    Returns the original record objects, in first-seen order.
    """
    seen = set()
    unique = []
    for record in records:
        key = tuple(_freeze(record.get(field)) for field in fields)
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


if __name__ == "__main__":
    events = [
        {"event_id": "e1", "source": "web", "tags": ["click"]},
        {"event_id": "e1", "source": "web", "tags": ["click"]},  # dup
        {"event_id": "e1", "source": "web", "tags": ["signup"]},  # not a dup
        {"event_id": "e2", "source": "web"},
    ]
    for event in dedupe_by_fields(events, ["event_id", "source", "tags"]):
        print(event)
