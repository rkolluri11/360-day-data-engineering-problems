"""Problem 5 — the wrong-model traps: races, GIL stalls, spawn costs
===================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Three traps, one root cause — the model fighting the workload:

  1. Threads on CPU-bound work: the GIL means threads take
     turns executing bytecode. Your "parallel" hash job uses
     one core and the wall clock doesn't move.
  2. Processes for tiny I/O tasks: spawning a process and
     pickling arguments costs milliseconds; the API call costs
     microseconds. Overhead eats the gain.
  3. asyncio with a blocking call: one ``time.sleep`` freezes
     the whole event loop — 10,000 coroutines wait on one task.

And the threading classic: ``counter += 1`` is read-modify-
write — three steps, never atomic. Two threads can read the
same value and one update vanishes. The fix is a ``Lock``:
only one thread inside the ``with`` block at a time.

Plain words: a race condition is two shoppers grabbing the last
ticket at once — the system counts two sales and prints one
ticket. The lock is the velvet rope: one at a time.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Races are silent: the counter is just... slightly off. No
    exception, no log line — dashboards drift and nobody
    knows. This is why shared counters need locks or atomics.
  - The GIL stall is silent too: CPU graphs show ONE hot core
    while 63 idle. If your "parallel" job pegs a single core,
    suspect the model before the code.
  - ``diagnose`` below encodes the traps as a code-review
    checklist: model + workload in, warning string out. Run it
    in review, not at 2 AM.
  - Locks don't compose for free: lock ordering across two
    locks can deadlock. One lock per shared structure, held
    briefly, is the boring strategy that ships.

Your solution: the counters and ``diagnose`` below are already
written. Read them, then run the tests: ``python -m pytest
tests -q`` from the day-16 folder. The racy counter uses a
barrier to force the interleaving — the lost update is
deterministic here, not a flaky prayer.

ANALOGY
-------
A lock is a bathroom key on a big hook: whoever holds it goes
in alone. Without it, two people walk in, one flush is
"counted" twice, and the plumbing log is fiction.
"""

import threading

THREADS = "threads"
PROCESSES = "processes"
ASYNCIO = "asyncio"
CPU_BOUND = "cpu_bound"
IO_BOUND = "io_bound"


def diagnose(model, kind, task_count=1):
    """Return a warning string when the model fights the workload, else None.

    model: THREADS, PROCESSES or ASYNCIO.
    kind: CPU_BOUND or IO_BOUND. task_count: concurrent units of work.
    """
    if model == THREADS and kind == CPU_BOUND:
        return ("GIL stall: threads take turns on CPU work — "
                "64 cores, one actually computing. Use processes.")
    if model == PROCESSES and kind == IO_BOUND and task_count < 100:
        return ("Spawn cost: pickling + process startup dwarfs tiny I/O tasks. "
                "Use threads or asyncio.")
    if model == ASYNCIO and kind == CPU_BOUND:
        return ("Loop freeze: one CPU-bound call blocks every coroutine. "
                "Use processes, or run it in an executor.")
    return None


class RacyCounter:
    """Demonstrates the lost update — deterministically.

    Both threads read self.value, then rendezvous at the barrier,
    then both write back read+1. One increment always vanishes.
    """

    def __init__(self):
        self.value = 0
        self._barrier = threading.Barrier(2)

    def increment(self):
        current = self.value
        self._barrier.wait(timeout=5)  # both threads read before either writes
        self.value = current + 1


class SafeCounter:
    """The same counter with a lock: read-modify-write becomes atomic."""

    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.value += 1
