"""Problem 4 — type the containers: generics name what's inside
===================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``counts = {}`` tells you nothing. Is it ``dict[str, int]`` (a counter),
``dict[str, list[float]]`` (batches per key), or ``dict[int, dict]``
(something to fear)? A bare ``dict`` is a black box; a parameterized
``dict[str, int]`` names the contents:

    Counter = dict[str, int]   # the alias IS the documentation

Stages compose when signatures line up: ``top_n`` takes the ``Counter``
that ``count_by`` returns, and the pairing is visible in the hints.

Plain words: ``dict[str, int]`` is the label on a filing cabinet drawer —
"invoices, filed by month" — versus a drawer labeled "stuff".

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Type ALIASES (``Counter = dict[str, int]``) are the cheapest
    documentation: one name, used everywhere, changed in one place.
    Use ``TypeAlias`` explicitly when the alias itself is the contract.
  - NESTED generics mirror nested data: ``dict[str, list[float]]`` is
    "batches of readings per sensor" — the warehouse shape, in the hint.
  - ``Callable`` types stages: ``Stage = Callable[[list[Row]], list[Row]]``
    means "anything from rows to rows". ``compose`` then wires stages with
    the contract enforced at check time.
  - mypy checks the CONTAINERS, not just the scalars: passing
    ``dict[int, str]`` where ``Counter`` is expected fails the build.

Your solution: ``count_by`` (rows -> Counter), ``top_n`` (Counter -> ranked
pairs), ``compose`` (stages -> pipeline), ``batch_stats`` (nested generics
-> per-key means). Then run the tests: ``python -m pytest tests -q`` from
the day-13 folder.

ANALOGY
-------
Generics are the manifest on a shipping container: not just "a container",
but "a refrigerated container holding 400 crates of apples". The dock crew
(untyped code) guesses; the manifest (hints) tells them before they open it.
"""

from collections.abc import Callable

Counter = dict[str, int]  # the alias IS the documentation
Row = dict[str, str]
Stage = Callable[[list[Row]], list[Row]]


def count_by(rows: list[Row], key: str) -> Counter:
    """Count rows by the value of ``key``: rows in, counter out."""
    counts: Counter = {}
    for row in rows:
        value = row[key]
        counts[value] = counts.get(value, 0) + 1
    return counts


def top_n(counts: Counter, n: int) -> list[tuple[str, int]]:
    """Rank a counter: the n most common (key, count) pairs, descending."""
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]


def compose(*stages: Stage) -> Stage:
    """Wire stages into a pipeline: each stage's output feeds the next.

    The ``Stage`` alias makes the contract visible: rows in, rows out,
    every step. A stage returning an int would fail the check.
    """

    def pipeline(rows: list[Row]) -> list[Row]:
        for stage in stages:
            rows = stage(rows)
        return rows

    return pipeline


def batch_stats(batches: dict[str, list[float]]) -> dict[str, float]:
    """Per-key mean across batches. Nested generics mirror nested data."""
    return {key: sum(vals) / len(vals) for key, vals in batches.items()}


if __name__ == "__main__":
    rows = [
        {"user_id": "u-1", "tier": "pro"},
        {"user_id": "u-2", "tier": "free"},
        {"user_id": "u-3", "tier": "pro"},
    ]
    counts = count_by(rows, "tier")
    print("counts:", counts)
    print("top 1:", top_n(counts, 1))

    def only_pro(rs: list[Row]) -> list[Row]:
        return [r for r in rs if r["tier"] == "pro"]

    pipe = compose(only_pro, only_pro)
    print("pipeline:", pipe(rows))
    print("stats:", batch_stats({"s1": [1.0, 3.0], "s2": [2.0]}))
