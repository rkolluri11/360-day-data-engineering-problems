"""Problem 3 — The callbacks that all said the last stage
=====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A ``lambda`` or nested function does not copy the loop variable — it
looks it up when it is **called**. So callbacks built in a loop all see
the loop variable's final value:

    funcs = [lambda: i for i in range(3)]
    [f() for f in funcs]   # [2, 2, 2] — not [0, 1, 2]

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
An ETL framework registers one validation callback per pipeline stage
in a loop:

    for stage in ["extract", "transform", "load"]:
        register(lambda: audit(stage))

Every failure audit then logs ``"load"``, no matter which stage failed —
silent wrong lineage in production logs. Fix ``build_stage_callbacks``
so each callback remembers its own stage.

Plain words: the buggy callbacks all share one sticky note that the
loop keeps rewriting; each one needs its own sticky note written at
the moment it is created.

ANALOGY
-------
It's like ten people sharing one whiteboard that keeps getting erased:
when each finally reads it, they all read the last thing written.
"""

from __future__ import annotations

from typing import Callable


def build_stage_callbacks(stages: list[str]) -> list[Callable[[], str]]:
    """Build one audit callback per pipeline stage.

    Each callback returns the name of the stage it belongs to, e.g.
    ``"stage=extract"``.
    """
    # The default-argument trick: ``stage=stage`` snapshots the current
    # value at definition time, giving each callback its own copy.
    return [lambda stage=stage: f"stage={stage}" for stage in stages]


if __name__ == "__main__":
    for cb in build_stage_callbacks(["extract", "transform", "load"]):
        print(cb())
