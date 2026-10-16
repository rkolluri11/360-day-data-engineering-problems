"""Problem 3 — name the absence: None is a value too
=======================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A column is sometimes empty. The hint says ``float``:

    def parse_amount(raw: str) -> float: ...

but ``None`` flows in anyway, and ``float(None)`` explodes — or the
``None`` slips through and poisons a sum three stages later. The fix is
to write the absence into the type:

    def parse_amount(raw: str | None) -> float | None: ...

Now the signature TELLS the caller: handle the None case. The ``| None``
is the billion-dollar mistake, defused by one character.

Plain words: ``| None`` is the "may contain nuts" label. Nobody is
surprised by the allergy warning when it's printed on the box.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``str | None`` (3.10+) == ``Optional[str]``. Prefer the pipe: it reads
    like what it means and nests cleanly (``list[str | None]``).
  - None PROPAGATES: one unhandled None in a transform becomes a None in
    the warehouse, then a NULL that breaks a dashboard join. Quarantine it
    at parse time — ``parse_amount`` decides the policy once.
  - ``coalesce`` (first non-None) is SQL's COALESCE brought into Python:
    the standard way to give absence a default without an if-ladder.
  - ``total_amounts`` shows the discipline: the None path is written down
    (skip), not discovered (crash). Sums never see a None.

Your solution: ``parse_amount`` (None/blank -> None, else float),
``coalesce`` (first non-None wins), ``total_amounts`` (sum skipping Nones).
Then run the tests: ``python -m pytest tests -q`` from the day-13 folder.

ANALOGY
-------
``| None`` is labeling the empty shelf in the warehouse: "this bin is
sometimes empty, and that's normal." Unlabeled, someone reaches in at
full speed expecting a box and dislocates a shoulder.
"""


def parse_amount(raw: str | None) -> float | None:
    """Parse a raw amount column. None and blanks mean 'no value' -> None.

    The None path is a documented return, not an accident.
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None
    return float(raw)


def coalesce(*values):
    """Return the first non-None value, or None if all are absent.

    SQL's COALESCE for Python: one expression instead of an if-ladder.
    """
    for value in values:
        if value is not None:
            return value
    return None


def total_amounts(raws: list[str | None]) -> float:
    """Sum a column of raw amounts, skipping absent values.

    The hint ``list[str | None]`` warns every caller: Nones are normal
    here. The loop never lets one reach the ``+=``.
    """
    total = 0.0
    for raw in raws:
        value = parse_amount(raw)
        if value is not None:
            total += value
    return total


if __name__ == "__main__":
    print(parse_amount("10.5"), parse_amount(None), parse_amount("   "))
    print("coalesce:", coalesce(None, None, 3), coalesce(None, None))
    print("total:", total_amounts(["1", None, "2.5", "", "3"]))
