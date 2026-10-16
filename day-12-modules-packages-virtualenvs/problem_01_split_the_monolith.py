"""Problem 1 — split the monolith: importing must not run the job
=================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline starts life as one file, ``pipeline.py`` — extract, transform,
load, all top level, with the run kicked off at the bottom of the file:

    rows = extract()          # top level: runs on IMPORT too
    save(load(transform(rows)))

The day someone writes ``from pipeline import extract`` to reuse one
function in a notebook, the whole job fires. Importing a module must be
side-effect free; running it is a separate, explicit act.

Plain words: importing a module should be like opening a cookbook —
you read a recipe, the oven does not turn on.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Top-level code runs at import time, ALWAYS — DB writes, API calls,
    even ``sys.exit()``. The ``if __name__ == "__main__":`` guard is the
    one-line boundary between "library" and "script".
  - ``python extract.py`` sets ``__name__ == "__main__"`` (guard runs);
    ``import extract`` sets ``__name__ == "extract"`` (guard skips).
  - The public surface is what you DEF: functions and constants.
    Everything else at top level is a liability.
  - Splitting one 800-line file into ``extract.py`` / ``transform.py`` /
    ``load.py`` is not cosmetics — it is what lets tests import one
    stage without executing the other two.

Your solution: ``render_flat_script()`` returns the BEFORE source
(top-level run, fires on import); ``render_guarded_module()`` returns
the AFTER source (same logic, guarded). Then run the tests:
``python -m pytest tests -q`` from the day-12 folder.

ANALOGY
-------
A module is a labeled moving box: the label (its name) tells you what is
inside, and nothing falls out until YOU open it (run it as __main__).
"""

FLAT_SCRIPT = '''\
"""pipeline.py — the monolith. One file, everything top level."""
SIDE_EFFECTS = []


def extract():
    """Pull one batch from the source."""
    return ["row1", "row2"]


# ---- top-level run: this fires on IMPORT, not just on execution ----
SIDE_EFFECTS.append("job ran at import time")
ROWS = extract()
'''

GUARDED_MODULE = '''\
"""extract.py — one stage, import-safe."""
SIDE_EFFECTS = []


def extract():
    """Pull one batch from the source."""
    return ["row1", "row2"]


def main():
    """The explicit entry point — runs only when asked."""
    SIDE_EFFECTS.append("job ran via main()")
    rows = extract()
    print("extracted", len(rows))
    return rows


if __name__ == "__main__":
    main()
'''


def render_flat_script():
    """The BEFORE: top-level code that executes on import."""
    return FLAT_SCRIPT


def render_guarded_module():
    """The AFTER: same logic, import-safe behind the __main__ guard."""
    return GUARDED_MODULE


def exec_as(source, module_name):
    """Execute source as if it were imported under ``module_name``.

    Returns the module namespace dict. ``module_name`` is what
    ``__name__`` becomes — ``"extract"`` for an import, ``"__main__"``
    for direct execution.
    """
    namespace = {"__name__": module_name}
    exec(compile(source, "<module>", "exec"), namespace)
    return namespace


if __name__ == "__main__":
    # BEFORE: importing the flat script runs the job.
    flat = exec_as(render_flat_script(), "pipeline")
    print("flat script, imported as module ->", flat["SIDE_EFFECTS"])

    # AFTER: importing the guarded module is silent...
    guarded = exec_as(render_guarded_module(), "extract")
    print("guarded module, imported as module ->", guarded["SIDE_EFFECTS"])

    # ...but running it as a script still works.
    print("guarded module, run as __main__:")
    exec_as(render_guarded_module(), "__main__")
