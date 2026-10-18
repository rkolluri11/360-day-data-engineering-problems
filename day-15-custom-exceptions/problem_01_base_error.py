"""Problem 1 — one base error: custom exceptions are just classes
================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Python exceptions are classes. ``raise ValueError("bad")`` builds an
object; ``except ValueError`` catches objects of that class (or any
subclass). A *custom* exception is simply a class you define:

    class PipelineError(Exception):
        "Base for every error this pipeline raises."

    class RowError(PipelineError):
        "One bad row - never fatal."

Why bother? A pipeline that catches bare ``Exception`` cannot tell
*your* errors from Python's own. ``except Exception`` also swallows
``MemoryError``-class surprises and — worst of all — your own bugs,
then reports success. With one base class, ``except PipelineError``
catches everything your pipeline can throw, and nothing else.

Plain words: a base error is a company badge. Every employee (error)
wears one; security (the except clause) checks badges, not faces.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Never write bare ``except:`` — it catches ``SystemExit`` and
    ``KeyboardInterrupt`` too, so Ctrl+C stops working and the run
    reports success anyway.
  - Never ``except Exception: pass`` — the error log stays empty while
    40,000 rows silently go missing. Silence is not handling.
  - Subclassing keeps compatibility: ``class ParseError(ValueError,
    PipelineError)`` still satisfies old code that catches
    ``ValueError``, while joining your taxonomy too.
  - ``is_pipeline_error(exc)`` is the portable check — ``isinstance``
    walks the whole hierarchy, so subclasses of subclasses count.

Your solution: the classes and helpers below are already written.
Read them, then run the tests: ``python -m pytest tests -q``
from the day-15 folder.

ANALOGY
-------
A base error is a hospital wristband system. Before triage, every
patient gets a band; afterwards, staff route by band color — nobody
re-diagnoses at the door.
"""


class PipelineError(Exception):
    """Base for every error this pipeline raises."""


class RowError(PipelineError):
    """One bad row. Never fatal: route it, keep the batch."""


class StageError(PipelineError):
    """The whole stage is broken (source down, temp failure). Retryable."""


class FatalError(PipelineError):
    """Stop the pipeline and page a human. Nothing else to do."""


def is_pipeline_error(exc):
    """True for anything wearing the pipeline badge — subclass or not."""
    return isinstance(exc, PipelineError)


def fail_row(reason):
    """Raise a row-level failure the way a transform would."""
    raise RowError(reason)
