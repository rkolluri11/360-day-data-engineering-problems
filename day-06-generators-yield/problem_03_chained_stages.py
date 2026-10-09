"""Problem 3 — The conveyor belt: chained stages
================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Day 5's pipeline loaded, cleaned, and parsed in separate passes — each
pass walked the whole dataset and often kept a copy. Generators let
you weld the stages into one belt:

    parsed = (parse(r) for r in read("events.jsonl"))
    clean = (c for c in parsed if valid(c))
    for row in clean:
        load(row)

``read`` yields a line, ``parse`` turns it into a dict, ``valid``
filters it, ``load`` consumes it — and at any instant only ONE row
exists. Adding a stage costs zero extra memory; it just extends the
belt.

Plain words: stations on an assembly line, not warehouses between them.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Chained laziness is pull-based, and pull-based systems have their own
failure modes:

  - **Pull-through waste:** if the final consumer only needs 100 rows
    (``islice``), upstream stages must not have read 10 million. A
    stage that pre-buffers (``sorted(gen)``, ``list(gen)``) breaks the
    chain silently.
  - **Exception mid-stream:** a poison row at position 9,999,999 has
    already been "processed" 9,999,998 rows downstream. Partial output
    exists. Your pipeline needs to say where it stopped — log the
    offset, or the rerun starts from zero.
  - **Teeing is not free:** ``itertools.tee`` on a 10M-row generator
    buffers everything the slower consumer hasn't read. Two consumers
    at different speeds = the whole file in memory again.

Your solution: ``pipeline(source, *stages)`` — chains generator
stages over *source*. Each stage is a function taking an iterable and
returning an iterable. Plus ``counting_source(n)`` — a generator of
``n`` items that records how many were actually pulled (proof of
pull-based laziness: take 3 from a 1M source and only 3 get read).

Plain words: the belt only moves when the last station asks for the
next item — nobody up front does extra work.

ANALOGY
-------
A sushi conveyor belt: the chef makes one plate when there's an empty
spot — never the whole evening's menu in advance.

YOUR TASK
---------
Implement ``pipeline`` and ``counting_source`` below. Then run the tests:
``python -m pytest tests -q`` from the day-06 folder.
"""


def pipeline(source, *stages):
    """Chain generator *stages* over *source*.

    Each stage is a callable: iterable -> iterable. Returns the final
    iterable. Stages execute lazily — nothing runs until consumed.
    """
    stream = source
    for stage in stages:
        stream = stage(stream)
    return stream


def counting_source(n):
    """Yield 0..n-1, tracking how many items were actually pulled.

    Returns (generator, counter) where counter is a one-element list
    holding the pull count. Pull 3 from a million and the counter
    reads 3 — laziness, proven.
    """
    counter = [0]

    def gen():
        for i in range(n):
            counter[0] += 1
            yield i

    return gen(), counter


if __name__ == "__main__":
    from itertools import islice

    def double(items):
        for x in items:
            yield x * 2

    def multiples_of_four(items):
        for x in items:
            if x % 4 == 0:
                yield x

    src, pulled = counting_source(1_000_000)
    result = pipeline(src, double, multiples_of_four)
    print(list(islice(result, 5)))  # [0, 4, 8, 12, 16]
    print("pulled from source:", pulled[0])  # 9 — only what the belt needed
