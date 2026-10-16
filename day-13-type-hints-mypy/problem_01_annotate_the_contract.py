"""Problem 1 — annotate the contract: a signature is a promise you can read
============================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline stage with no hints tells you nothing until you read its body:

    def load(rows, dest): ...

What is ``rows`` — a list? a generator? a filename? What does it return?
Every caller guesses, and every guess is a future 2 AM page. Annotations
turn the signature into documentation:

    def load(rows: list[dict], dest: str) -> int: ...

Now a reader knows the deal before opening the body.

Plain words: annotations are the label on the box. You read what goes in
and what comes out without unpacking it.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Annotations are METADATA, not enforcement. ``__annotations__`` stores
    them; the interpreter ignores them. ``load("oops", 42)`` RUNS.
    mypy is the enforcer; Python is not.
  - ``typing.get_type_hints(fn)`` resolves annotations to real objects
    (strings become types, ``from __future__ import annotations`` safe).
  - Hint the BOUNDARIES: public functions, stage inputs/outputs, anything
    another team calls. Private helpers can stay light.
  - ``-> None`` is a hint too — it says "this mutates or logs; it returns
    nothing useful." Callers stop assigning its result.

Your solution: ``describe_signature(fn)`` renders the contract as text,
and ``prove_runtime_ignores()`` shows hints don't gate execution — the
checker does (see problem 5). Then run the tests:
``python -m pytest tests -q`` from the day-13 folder.

ANALOGY
-------
An annotated signature is a nutrition label: serving size, ingredients,
calories — printed on the box, no tasting required. Unannotated code is
a mystery can: you find out what's inside by opening it.
"""

from typing import get_type_hints


def extract(source: str) -> list[dict]:
    """Pull one batch of raw rows from a source."""
    return [{"user_id": "u-1", "amount": "10.5"}]


def transform(rows: list[dict]) -> list[dict]:
    """Clean one batch of rows."""
    return rows


def load(rows: list[dict], dest: str) -> int:
    """Write rows to dest; return the count written."""
    return len(rows)


def _hint_name(hint) -> str:
    """Render one annotation the way a reader would say it."""
    if hint is None:
        return "None"
    s = str(hint).replace("typing.", "")
    if s.startswith("<class "):
        return getattr(hint, "__name__", s)
    return s


def describe_signature(fn) -> dict:
    """Return fn's contract as {parameter: annotation-name, ..., 'return': ...}.

    Unannotated parameters are reported as "unannotated" — the label is
    missing, which is itself information.
    """
    hints = get_type_hints(fn)
    contract = {}
    for param in fn.__code__.co_varnames[: fn.__code__.co_argcount]:
        contract[param] = _hint_name(hints[param]) if param in hints else "unannotated"
    contract["return"] = (
        _hint_name(hints["return"]) if "return" in hints else "unannotated"
    )
    return contract


def prove_runtime_ignores() -> int:
    """Call load() with wrong-typed args. It still runs — hints don't gate.

    Returns the (nonsensical) result. mypy would flag this call; the
    interpreter happily computes len("abc") == 3.
    """
    return load("abc", 123)  # type: ignore[arg-type]


if __name__ == "__main__":
    print("load contract:", describe_signature(load))
    print("extract contract:", describe_signature(extract))
    print("wrong-typed call still runs ->", prove_runtime_ignores())
    print("annotations are metadata:", load.__annotations__)
