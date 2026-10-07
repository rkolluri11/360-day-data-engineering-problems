"""Problem 5 — The pipeline made of functions
========================================

THE PROBLEM (beginner foothold first)
------------------------------------
Chain two functions:

    def compose(f, g):
        return lambda x: g(f(x))

``compose(clean, validate)`` is a new function that cleans, then
validates. Composition builds big behavior from small, testable
pieces instead of one giant function.

Plain words: snap two garden hoses together instead of buying a
longer hose.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your ETL is 12 stages: extract, validate, dedupe, enrich, ...
Each stage is ``stage(rows, **ctx)`` — rows in, rows out, with a
shared context (``run_id``, ``env``, ``dry_run``). Today the code
is:

    data = extract(source)
    data = validate(data)
    data = dedupe(data)
    ...

At 2 AM ``dedupe`` raises ``ValueError`` on a poison row. The
traceback shows the error — but not WHICH stage failed, what its
input looked like, or the ``run_id``. You grep logs for an hour.

Your solution: ``pipeline(*stages)`` — a higher-order function
that composes stages into one callable ``run(rows, **ctx)`` with:

  1. context threading: every stage receives the same ``**ctx``;
  2. error attribution: a stage failure raises ``StageError`` naming
     the stage (by ``__name__`` or an explicit ``(name, fn)`` tuple),
     its index, and the input size — chained to the original
     exception via ``raise ... from``;
  3. ``StageError`` itself passes through unwrapped (no double
     wrapping when pipelines nest inside pipelines);
  4. an empty pipeline returns its input unchanged;
  5. ``run.stages`` lists the stage names for observability.

Plain words: the assembly line now stamps every crate with the
station number. When a crate jams, you know exactly which station,
how far the line got, and which shift it was — without replaying
the whole night.

ANALOGY
-------
A sushi conveyor belt with a camera over each chef. If a plate
comes back wrong, you don't interrogate the whole restaurant —
you check the camera at station 4, see the order ticket (the
run_id), and know whose hands touched it last.
"""

from __future__ import annotations


class StageError(Exception):
    """A pipeline stage failed: which one, where, and why."""

    def __init__(self, stage_name, index, n_input, original):
        self.stage_name = stage_name
        self.index = index
        self.n_input = n_input
        self.original = original
        super().__init__(
            f"stage {index} ({stage_name!r}) failed on {n_input} input "
            f"row(s): {original!r}"
        )


def _split(stage):
    if isinstance(stage, tuple):
        name, fn = stage
        return name, fn
    return getattr(stage, "__name__", repr(stage)), stage


def pipeline(*stages):
    """Compose ``stage(rows, **ctx)`` functions into one callable.

    Returns ``run(rows, **ctx)`` threading ctx through every stage.
    Failures become StageError with the stage name, index, and input
    size, chained to the original exception.
    """
    names = [_split(s)[0] for s in stages]

    def run(rows, **ctx):
        data = rows
        for index, stage in enumerate(stages):
            name, fn = _split(stage)
            try:
                n_in = len(data) if hasattr(data, "__len__") else "?"
                data = fn(data, **ctx)
            except StageError:
                raise  # already attributed (nested pipeline)
            except Exception as exc:
                raise StageError(name, index, n_in, exc) from exc
        return data

    run.stages = names
    return run


# --- Example stages ------------------------------------------------------

def extract(source, **ctx):
    return [{"id": i, "raw": f"row-{i}"} for i in range(5)]


def validate(rows, **ctx):
    for row in rows:
        if "id" not in row:
            raise ValueError(f"missing 'id': {row}")
    return rows


def tag(rows, **ctx):
    return [{**r, "run_id": ctx.get("run_id")} for r in rows]


if __name__ == "__main__":
    etl = pipeline(("extract", extract), validate, ("tag", tag))
    print("stages:", etl.stages)
    for row in etl("s3://bucket/orders", run_id="run-42"):
        print(row)

    bad = pipeline(validate)
    try:
        bad([{"nope": 1}], run_id="run-43")
    except StageError as e:
        print("caught:", e)
        print("original was:", repr(e.__cause__))
