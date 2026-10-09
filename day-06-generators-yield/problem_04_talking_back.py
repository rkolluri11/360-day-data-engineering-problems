"""Problem 4 — Talking back: send() and close()
================================================

THE PROBLEM (beginner foothold first)
------------------------------------
So far generators only flow one way: out. But ``yield`` is also an
expression — it can *receive* a value:

    def averager():
        total = 0.0
        count = 0
        while True:
            value = yield total / count if count else 0.0
            total += value
            count += 1

    avg = averager()
    next(avg)          # prime it — runs to the first yield
    avg.send(10)       # value lands in `value`; yields 10.0
    avg.send(20)       # yields 15.0

``send()`` pushes data *into* a paused generator and resumes it. This
turns a generator into a tiny stateful service: running stats,
rate limiters, circuit breakers — all without a class.

Plain words: a mailbox, not just a conveyor belt — you can post
letters back upstream.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Two-way generators have protocol rules that bite:

  - You must **prime** the generator with ``next()`` before the first
    ``send()`` — sending to a just-created generator raises
    ``TypeError: can't send non-None value to a just-started
    generator``. Forget this once and you'll never forget it again.
  - ``close()`` throws ``GeneratorExit`` at the paused ``yield``.
    If the generator catches it and yields again, Python raises
    ``RuntimeError``. Cleanup code (flushing a buffer, closing a
    file) belongs in ``try/finally`` around the loop — and it must
    not yield.
  - A closed or exhausted generator silently ignores further
    ``send()`` — it raises ``StopIteration``. Code that keeps sending
    after shutdown gets a confusing exception far from the bug.

Your solution: ``running_stats()`` — a primed-by-you coroutine that
accepts numbers via ``send()`` and yields ``(count, mean)`` after
each. It must:
  - start primed (calling ``running_stats()`` returns a generator
    ready to receive — no manual ``next()`` needed by the caller),
  - ignore non-numeric sends (count them as ``skipped`` and keep going),
  - flush its final ``(count, mean, skipped)`` triple into a
    ``result`` list on ``close()`` via try/finally (no yield after
    close).

Plain words: the tally clerk who keeps counting while you shout
numbers, and hands you the final sheet when you say "done".

ANALOGY
-------
A drive-through intercom: you talk, it answers, and when you say
"that's all" it prints the receipt — the window never needed to
hold every car.

YOUR TASK
---------
Implement ``running_stats`` below. Then run the tests:
``python -m pytest tests -q`` from the day-06 folder.
"""


def running_stats():
    """Coroutine: send numbers in, get (count, mean) out after each.

    Returns (generator, result) — the generator is already primed.
    Non-numeric sends are skipped (counted). On close(), appends the
    final (count, mean, skipped) triple to *result* via try/finally.
    """
    result = []

    def _gen():
        total = 0.0
        count = 0
        skipped = 0
        try:
            value = yield  # prime point: first next() lands here
            while True:
                try:
                    total += float(value)
                    count += 1
                except (TypeError, ValueError):
                    skipped += 1
                mean = total / count if count else 0.0
                value = yield (count, mean)
        finally:
            mean = total / count if count else 0.0
            result.append((count, mean, skipped))

    gen = _gen()
    next(gen)  # prime it — the caller never has to
    return gen, result


if __name__ == "__main__":
    stats, final = running_stats()
    print(stats.send(10))       # (1, 10.0)
    print(stats.send(20))       # (2, 15.0)
    print(stats.send("oops"))   # (2, 15.0) — skipped, not crashed
    stats.close()
    print(final)                # [(2, 15.0, 1)]
