"""Problem 1 — pick the model: the decision table as code
================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Python gives you three concurrency models, and they are not
interchangeable:

  - threading: many threads, ONE process, shared memory. The GIL
    (Global Interpreter Lock) lets only one thread run Python
    bytecode at a time — but a thread waiting on the network
    RELEASES the GIL, so other threads keep working.
  - multiprocessing: many processes, separate memory. No GIL
    problem — true parallelism — but spawning is expensive and
    everything crossing the boundary must pickle.
  - asyncio: ONE thread, one event loop, many coroutines. A
    coroutine waiting on I/O yields control; nothing blocks.
    Cheapest per task, but one CPU-bound call freezes the loop.

So the choice is a function of the WORK, not of taste:

  - CPU-bound (hashing, parsing, compression) -> processes
  - I/O-bound, hundreds of tasks (API fan-out) -> threads
  - I/O-bound, thousands of waiters -> asyncio

Plain words: don't pick the vehicle before you know the cargo.
A sports car, a truck and a cargo ship all move things — the
cargo decides.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Threads on CPU-bound work is the classic 1%-of-64-cores bug:
    the code "parallelizes" and the wall clock doesn't move.
  - Processes for 10,000 tiny API calls: spawn plus pickle
    overhead dwarfs the work; threads or asyncio finish first.
  - asyncio with one blocking call (time.sleep, requests.get)
    freezes EVERY coroutine — the whole loop waits on one task.
  - Shared mutable state across processes silently diverges:
    each process owns its own copy; use queues, pipes, or
    shared memory explicitly.

Your solution: the decision function below is already written.
Read the table, then run the tests: ``python -m pytest tests -q``
from the day-16 folder.

ANALOGY
-------
Threads are cooks sharing one kitchen — fast until two grab the
same knife. Processes are separate kitchens — no sharing, no
fights, rent per kitchen. Asyncio is one cook who starts the
pasta, chops vegetables while it boils, and never stands idle.
"""

CPU_BOUND = "cpu_bound"
IO_BOUND = "io_bound"

THREADS = "threads"
PROCESSES = "processes"
ASYNCIO = "asyncio"

# Thousands of concurrent waiters is where per-thread overhead
# starts to hurt and asyncio earns its keep.
ASYNCIO_THRESHOLD = 1000


def pick_model(kind, task_count=1):
    """Return THREADS, PROCESSES or ASYNCIO for the workload.

    kind: CPU_BOUND (hashing, parsing) or IO_BOUND (API, downloads).
    task_count: how many concurrent units of work.
    """
    if kind == CPU_BOUND:
        return PROCESSES
    if task_count >= ASYNCIO_THRESHOLD:
        return ASYNCIO
    return THREADS


def explain(model):
    """One-line reason the model fits — the comment you'd leave in code."""
    return {
        THREADS: "I/O-bound: threads release the GIL while waiting; memory is shared.",
        PROCESSES: "CPU-bound: processes sidestep the GIL for true parallelism.",
        ASYNCIO: "Thousands of waiters: one loop, no per-task thread overhead.",
    }[model]
