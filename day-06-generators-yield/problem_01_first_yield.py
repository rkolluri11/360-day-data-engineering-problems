"""Problem 1 — The function that pauses
======================================

THE PROBLEM (beginner foothold first)
------------------------------------
A normal function runs to the end and hands you ONE result:

    def read_all(lines):
        rows = []
        for line in lines:
            rows.append(line.strip())
        return rows

If ``lines`` has 10 million entries, ``rows`` holds 10 million strings
*before you see the first one*. The memory graph climbs to the top of
the chart and stays there.

``yield`` changes the deal. A function with ``yield`` in it does not
run when you call it — it returns a *generator object*, frozen at the
start. Nothing executes until you ask for the first item:

    def read_rows(lines):
        for line in lines:
            yield line.strip()

``gen = read_rows(lines)`` costs almost nothing. ``next(gen)`` runs
the function until the first ``yield``, hands you that value, and
freezes again — local variables intact. Each item is produced on
demand and can be forgotten the moment you move on.

Plain words: a list is a warehouse that must be filled before the
truck leaves. A generator is a conveyor belt — one item appears,
you handle it, it's gone.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Laziness is a contract you can accidentally break:

  - Calling ``list(gen)`` or iterating twice silently materializes
    everything — the memory win evaporates and nothing warns you.
  - A generator is single-pass: after it's exhausted, ``next()``
    raises ``StopIteration``. Code that assumes re-iteration gets an
    empty pipeline and a confusingly correct-looking empty result.
  - Exceptions inside the generator surface at the *consumer's*
    ``next()`` call, not where the generator was created — so the
    traceback points at your loop, and the real failure is upstream.

Your solution: ``read_rows(lines)`` — yields each stripped, non-empty
line. And ``first_n(gen, n)`` — returns the first n items as a list
*without* consuming the rest of the generator (proving you only ever
pull what you need).

Plain words: sip through a straw, not the whole milkshake at once.

ANALOGY
-------
A vending machine vs. a buffet: the list makes you carry the entire
buffet home before you eat; the generator dispenses one item per
button press.

YOUR TASK
---------
Implement ``read_rows`` and ``first_n`` below. Then run the tests:
``python -m pytest tests -q`` from the day-06 folder.
"""


def read_rows(lines):
    """Yield stripped, non-empty lines from *lines*, lazily."""
    for line in lines:
        stripped = line.strip()
        if stripped:
            yield stripped


def first_n(gen, n):
    """Return the first *n* items of generator *gen* as a list.

    Pulls at most *n* items — the generator is left paused, not drained.
    """
    out = []
    for _ in range(n):
        try:
            out.append(next(gen))
        except StopIteration:
            break
    return out


if __name__ == "__main__":
    # A "10 million line file" that costs nothing to create:
    def fake_file():
        i = 0
        while True:
            yield f"  row-{i}  "
            i += 1

    gen = read_rows(fake_file())
    print(first_n(gen, 3))          # ['row-0', 'row-1', 'row-2']
    print(next(gen))               # row-3 — the generator kept going
    print(type(gen))               # a generator object, ~100 bytes, not 10M rows
