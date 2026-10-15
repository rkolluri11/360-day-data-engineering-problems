"""Problem 3 — @timer: untimed stages silently eat your SLA
============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Your pipeline has five stages and a 30-minute SLA. It finishes in 47.
Which stage is slow? Without per-stage timing you are guessing — and
guessing means optimizing the wrong stage. A ``@timer`` decorator
records how long each decorated function actually took:

    @timer("extract", TIMINGS)
    def extract(): ...

Plain words: a stopwatch taped to each stage, with the readings saved
in a notebook instead of shouted across the room.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The duration must be recorded in a ``finally`` — a stage that
    THROWS is exactly the stage whose timing you need, and an
    exception must never delete the evidence (or be swallowed).
  - The clock is injected (``time.perf_counter`` by default). Real
    clocks make flaky tests; a fake clock makes durations exact.
  - One registry entry per stage NAME, each holding a LIST — because
    the same stage runs many times (retries, batches) and you want a
    distribution, not a single overwritten number.
  - ``functools.wraps`` again — timers must not rename your stages.

Your solution: ``StageTimer`` and the ``timer(stage, registry, clock)``
decorator factory. Then run the tests: ``python -m pytest tests -q``.

ANALOGY
-------
A decorator is gift wrap — this one wraps the stage in a stopwatch.
You don't change what's inside the box; you just know exactly how
long the box took to open, even when it caught fire.
"""

import time
from functools import wraps


class StageTimer:
    """Notebook of stage durations: name -> list of seconds, in order."""

    def __init__(self, clock=time.perf_counter):
        self.clock = clock
        self.durations = {}

    def record(self, stage, seconds):
        self.durations.setdefault(stage, []).append(seconds)

    def total(self, stage):
        return sum(self.durations.get(stage, []))


def timer(stage, registry=None, clock=time.perf_counter):
    """Decorator: time every call, recording into ``registry``.

    ``registry`` is a ``StageTimer`` (a fresh one is created if omitted).
    Durations are recorded even when the function raises; the exception
    propagates unchanged.
    """
    if registry is None:
        registry = StageTimer(clock)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = clock()
            try:
                return fn(*args, **kwargs)
            finally:
                registry.record(stage, clock() - start)

        return wrapper

    return decorator


class FakeClock:
    """Deterministic clock for tests: each call advances by ``step``."""

    def __init__(self, step=0.5):
        self.now = 0.0
        self.step = step

    def __call__(self):
        t = self.now
        self.now += self.step
        return t


if __name__ == "__main__":
    clock = FakeClock(step=2.0)
    timings = StageTimer(clock)

    @timer("extract", timings, clock)
    def extract():
        return ["row"]

    @timer("load", timings, clock)
    def load():
        raise RuntimeError("warehouse down")

    print(extract())                      # ['row']
    try:
        load()
    except RuntimeError:
        pass
    print(timings.durations)              # {'extract': [2.0], 'load': [2.0]}
