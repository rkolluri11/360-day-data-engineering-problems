"""Problem 3 — process pool: real parallelism for CPU-bound work
===============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Hashing a million records is CPU-bound: the work happens IN the
interpreter, so the GIL never releases and threads just take
turns. ``ProcessPoolExecutor`` spawns real processes — each with
its own interpreter and its own GIL — so 8 workers hash on 8
cores at once.

The price: processes don't share memory. Arguments and results
cross the boundary pickled, so the worker function must live at
module level (lambdas and closures can't pickle) and big
arguments get copied per task.

Plain words: threads are roommates sharing one stove — great
for waiting on deliveries, useless when everyone must cook.
Processes are separate apartments: everyone cooks at once, but
you carry the groceries up yourself.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The worker function MUST be importable: define it at module
    level. A lambda or nested closure fails with PicklingError
    at submit time — after you've already paid to spawn.
  - Guard the entry point with ``if __name__ == "__main__":``.
    On spawn-based platforms workers re-import your module; an
    unguarded script re-runs the whole pipeline per worker.
  - Chunk the work: one process per row means pickle overhead
    per row. ``pool.map`` already chunks; for tiny items raise
    ``chunksize`` so IPC doesn't dwarf compute.
  - Memory multiplies: 8 workers each holding a copy of a 2 GB
    frame is 16 GB. Stream records in, don't preload the world.

Your solution: ``hash_records`` below is already written. Read
it, then run the tests: ``python -m pytest tests -q`` from the
day-16 folder.

ANALOGY
-------
A process pool is eight separate kitchens with one recipe book:
every cook works at full speed, but the recipe (the function)
must be written down where everyone can read it — no whispered
instructions across the wall.
"""

import hashlib
from concurrent.futures import ProcessPoolExecutor


def sha256_record(record):
    """CPU-bound transform: hash a record's canonical form.

    Module-level on purpose — lambdas and closures can't cross
    the process boundary; this one pickles cleanly.
    """
    canonical = "|".join(f"{k}={record[k]}" for k in sorted(record))
    return hashlib.sha256(canonical.encode()).hexdigest()


def hash_records(records, max_workers=4):
    """Hash every record across processes. Result order matches input."""
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(sha256_record, records))
