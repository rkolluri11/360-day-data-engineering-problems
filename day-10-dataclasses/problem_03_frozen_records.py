"""Problem 3 — Frozen records between stages
=========================================

THE PROBLEM (beginner foothold first)
------------------------------------
A record dict flows through three pipeline stages. Stage 2 "helpfully"
normalizes a field in place — and stage 3 now sees mutated data it never
asked for. Nobody owns the mutation; everybody inherits the confusion.
Debugging means diffing the record at every handoff.

``frozen=True`` makes the record immutable: any write attempt raises
``FrozenInstanceError`` at the exact line of the crime, with a stack
trace pointing at the offender. Frozen records are also hashable, so
they work as dict keys and in sets — free dedup.

Plain words: frozen records can't be vandalized in transit.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Frozen is SHALLOW: a frozen dataclass holding a list still lets
    callers mutate the list. Freeze the container AND the contents
    (tuples, not lists) or the immutability is theater.
  - To "change" a frozen record, use ``dataclasses.replace()`` — it
    builds a new record with chosen fields swapped. The original is
    untouched, so stage 2's tweak can't leak into stage 3.
  - ``eq=True`` (the default) plus ``frozen=True`` gives you hashing:
    identical records collapse in a set, which is a one-line dedup
    at any stage boundary.

Your solution: three helpers over the ``Record`` dataclass below —
``try_mutate(record)`` returns True if a write attempt raised
``FrozenInstanceError``; ``dedup(records)`` returns unique records
preserving first-seen order; ``rename(record, new_payload)`` returns a
NEW record with ``payload`` swapped via ``replace()``.

Plain words: can't touch this, dedup for free, change by copying.

ANALOGY
-------
A frozen record is a sealed evidence bag: anyone can carry it, nobody
can slip something into it, and the seal number (the hash) tells you
instantly if you've seen this bag before.

YOUR TASK
---------
Implement the three helpers below. Then run the tests:
``python -m pytest tests -q`` from the day-10 folder.
"""

from dataclasses import dataclass, FrozenInstanceError, replace


@dataclass(frozen=True)
class Record:
    id: int
    payload: str


def try_mutate(record):
    """True if attempting record.payload = 'x' raises FrozenInstanceError."""
    try:
        record.payload = "x"
    except FrozenInstanceError:
        return True
    return False


def dedup(records):
    """Unique records, first-seen order (relies on frozen hashing)."""
    seen = set()
    out = []
    for r in records:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def rename(record, new_payload):
    """A NEW Record with payload swapped; the original is untouched."""
    return replace(record, payload=new_payload)


if __name__ == "__main__":
    r = Record(1, "raw")
    print(try_mutate(r))                       # True — write refused
    print(dedup([r, r, Record(2, "raw")]))      # 2 unique records
    r2 = rename(r, "clean")
    print(r2, "| original:", r)                # original unchanged
