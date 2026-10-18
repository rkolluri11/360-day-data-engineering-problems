"""Problem 4 — the except clause is a routing table
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Yesterday's lesson (Day 14): a bad row must not kill the batch — route
it with a reason. Today's machinery: the ``except`` clauses ARE the
router. One clause per fate:

    try:
        clean.append(transform(row))
    except RowError as e:        # bad row -> quarantine, keep going
        quarantined.append({**row, "_reason": str(e)})
    except StageError as e:      # broken stage -> count it, maybe escalate
        stage_errors += 1
        if stage_errors > error_budget:
            raise FatalError(f"stage failed {stage_errors} times: {e}")
    # FatalError is NOT caught here - it stops the line, as it should.

A stage that fails a few times is flaky; a stage that fails past its
error *budget* is dead. The budget turns "retry forever" into "page a
human".

Plain words: the except chain is a bouncer with a list. Row errors get
the side door with a stamp; stage errors get three strikes; fatal
errors close the club.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Sibling classes need no ordering tricks — ``RowError`` and
    ``StageError`` never overlap — but a parent ``PipelineError`` clause
    must come AFTER its subclasses, or it eats every branch.
  - The quarantine row keeps ``_reason``: the *string* of the error,
    not the exception object. Quarantine tables are data, and exception
    objects do not serialize.
  - Raising ``FatalError`` inside ``except StageError`` chains the
    errors automatically (``__context__``) — the on-call sees the whole
    trail, not just the last hop.
  - The receipt still balances: ``len(rows) == len(clean) +
    len(quarantined)`` — nothing vanishes, even when the stage burns.

Your solution: ``clean_batch(rows, transform, error_budget=3)`` below.
Then run the tests: ``python -m pytest tests -q`` from the day-15 folder.

ANALOGY
-------
An error budget is a fuse box. A few surges trip and reset; past the
budget the main breaker throws — and you call an electrician, not
another reset.
"""

from problem_01_base_error import FatalError, RowError, StageError


def clean_batch(rows, transform, error_budget=3):
    """Run a stage, routing by exception type.

    Returns (clean, quarantined). RowErrors are quarantined with a
    reason; StageErrors accumulate against the budget and escalate to
    FatalError past it; FatalError stops the line immediately.
    """
    clean, quarantined = [], []
    stage_errors = 0
    for row in rows:
        try:
            clean.append(transform(row))
        except RowError as e:
            quarantined.append({**row, "_reason": str(e)})
        except StageError as e:
            stage_errors += 1
            if stage_errors > error_budget:
                raise FatalError(
                    f"stage failed {stage_errors} times (budget {error_budget}): {e}"
                )
    return clean, quarantined
