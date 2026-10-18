"""Problem 2 — three severities, three fates: the routing table
=================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Not every failure deserves the same response. A pipeline has (at least)
three kinds of bad news:

    RowError   -> one bad row    -> QUARANTINE the row, keep the batch
    StageError -> a broken stage -> RETRY the stage (it may heal)
    FatalError -> dead pipeline  -> HALT everything, page a human

The router maps an exception to its fate. Read it top to bottom: it is
the pipeline's policy written as code, not a comment.

Plain words: the routing table is airport triage. Green wristband walks
on, yellow gets watched, red stops the line — nobody guesses severity
from a scream.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Order matters in ``except`` chains: put the most specific class
    first. ``except PipelineError`` before ``except RowError`` would
    swallow the specific branch — the router would always say
    "quarantine" for fatal news.
  - ``isinstance`` walks subclasses, so a ``TransientError(StageError)``
    routes to "retry" without a special case. That is the point of the
    hierarchy: new errors inherit sane fates.
  - An *unknown* exception type is itself fatal news. The router raises
    ``TypeError`` loudly instead of guessing — guessing is how pipelines
    report success with half their data missing.
  - Fates are strings here for readability ("quarantine" / "retry" /
    "halt"); in production they become handlers — functions, not words.

Your solution: ``route_error(exc)`` below. Then run the tests:
``python -m pytest tests -q`` from the day-15 folder.

ANALOGY
-------
``route_error`` is a sorting office. Every letter (exception) arrives
with a stamp (its class); the sorter never opens the envelope — the
stamp decides the bin.
"""

from problem_01_base_error import FatalError, PipelineError, RowError, StageError

QUARANTINE = "quarantine"
RETRY = "retry"
HALT = "halt"


def route_error(exc):
    """Map an exception to its fate: quarantine, retry, or halt.

    Most specific first; an unknown type raises TypeError — loudly —
    instead of being guessed at.
    """
    if isinstance(exc, RowError):
        return QUARANTINE
    if isinstance(exc, StageError):
        return RETRY
    if isinstance(exc, FatalError):
        return HALT
    raise TypeError(f"unknown error type: {type(exc).__name__}")
