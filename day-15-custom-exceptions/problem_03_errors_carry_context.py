"""Problem 3 — errors carry context: the message names the culprit
======================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``raise RowError("bad row")`` tells you nothing at 2 AM. *Which* row?
Which stage? How many attempts in? Exceptions can carry that context —
they are objects, so give them attributes:

    class DetailedRowError(RowError):
        def __init__(self, row, stage, reason):
            super().__init__(f"[{stage}] row {row.get('id')}: {reason}")
            self.row = row
            self.stage = stage
            self.reason = reason

Now the log line reads ``[parse] row u-404: bad amount 'abc'`` — the
culprit is in the message, and the row is on the object for whoever
quarantines it.

Plain words: a context-carrying error is a package with a shipping
label. The warehouse (handler) never opens it to decide where it goes.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Build the message in ``__init__`` and keep the raw fields too.
    Logs are text; handlers need objects. One source, both forms.
  - Never put PII in the message (full payloads leak into logs).
    Carry the row *object* on the exception for code, and a scrubbed
    identifier in the message for humans.
  - ``attempt`` counts retries: "timeout (attempt 3 of 4)" tells the
    reader whether the next failure pages someone or retries again.
  - ``repr`` of a dict in the message truncates poorly; format the
    fields you need explicitly.

Your solution: ``DetailedRowError`` below. Then run the tests:
``python -m pytest tests -q`` from the day-15 folder.

ANALOGY
-------
An error without context is a fire alarm with no floor number — the
whole building evacuates. With context, it is a sprinkler map: the
right floor, the right room.
"""

from problem_01_base_error import PipelineError, RowError


class DetailedRowError(RowError):
    """A row failure that names its culprit: stage, row id, reason."""

    def __init__(self, row, stage, reason, attempt=1):
        super().__init__(f"[{stage}] row {row.get('id')}: {reason}")
        self.row = row
        self.stage = stage
        self.reason = reason
        self.attempt = attempt

    def label(self):
        """Human-readable one-liner with the retry position."""
        return f"[{self.stage}] row {self.row.get('id')}: {self.reason} (attempt {self.attempt})"


def fail_parse(row, reason):
    """Raise a parse-stage row failure the way a real stage would."""
    raise DetailedRowError(row, stage="parse", reason=reason)
