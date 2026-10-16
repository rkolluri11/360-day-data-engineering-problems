"""Problem 2 — shape the row: dict-shaped records get a schema
===================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Pipeline rows travel as bare dicts:

    {"user_id": "u-1", "amount": "10.5"}

Nothing says which keys must exist, which are optional, or what types the
values are. Upstream renames ``amount`` to ``total`` and every downstream
stage fails with ``KeyError`` — or worse, ``.get("amount")`` silently
yields ``None`` and the corruption flows on. A ``TypedDict`` writes the
row's shape down in one place:

    class RawRow(TypedDict):
        user_id: str
        amount: str

Plain words: a TypedDict is the seating chart for a dict — every seat
labeled, so a missing guest is noticed at the door, not at dessert.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``TypedDict`` is a CHECK-TIME construct. At runtime it is still a
    plain dict: extra keys are allowed, missing keys raise KeyError only
    when accessed. The schema lives in the hints, enforced by mypy.
  - ``total=False`` marks optional keys (new upstream columns don't break
    old readers); ``Required[]``/``NotRequired[]`` pin individual keys.
  - Schema drift is a DATA problem: validate at the boundary. ``validate_row``
    below flags missing required keys AND unexpected keys — the two shapes
    drift takes.
  - One module owns the row types. Import the shape; don't re-spell the
    keys in every stage.

Your solution: ``RawRow`` / ``EventRow`` declare the shapes;
``validate_row(row, required, allowed)`` returns human-readable problems
(``"missing: amount"``, ``"unexpected: discount"``); ``row_shape()``
reads the schema back off the TypedDict. Then run the tests:
``python -m pytest tests -q`` from the day-13 folder.

ANALOGY
-------
A TypedDict is an airport customs form: name every item you're carrying.
Undeclared items (unexpected keys) and missing declarations (missing keys)
get flagged at the border — the pipeline boundary — not after landing.
"""

from typing import TypedDict


class RawRow(TypedDict):
    """The shape every extract stage promises to produce."""

    user_id: str
    amount: str


class EventRow(TypedDict, total=False):
    """Upstream events: user_id required by readers, the rest optional."""

    user_id: str
    amount: str
    currency: str


def row_shape(td: type) -> dict:
    """Read the schema back off a TypedDict: {key: type-name}."""
    return {k: v.__name__ for k, v in td.__annotations__.items()}


def validate_row(row: dict, required: set, allowed: set) -> list[str]:
    """Flag schema drift at the boundary.

    Returns problems like "missing: amount" (required key absent) and
    "unexpected: discount" (key outside the declared shape). A clean row
    returns []. Sorted for deterministic output.
    """
    problems = []
    for key in sorted(required - set(row)):
        problems.append(f"missing: {key}")
    for key in sorted(set(row) - allowed):
        problems.append(f"unexpected: {key}")
    return problems


RAW_REQUIRED = {"user_id", "amount"}
RAW_ALLOWED = {"user_id", "amount", "currency"}


def check_raw_row(row: dict) -> list[str]:
    """Validate one row against the RawRow contract."""
    return validate_row(row, RAW_REQUIRED, RAW_ALLOWED)


if __name__ == "__main__":
    print("RawRow shape:", row_shape(RawRow))
    print("EventRow shape:", row_shape(EventRow))
    good = {"user_id": "u-1", "amount": "10.5"}
    drifted = {"user_id": "u-2", "discount": "5"}  # amount renamed upstream
    print("good row ->", check_raw_row(good))
    print("drifted row ->", check_raw_row(drifted))
