"""Problem 3 — absolute imports: run it as a module, not a script
==================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Inside the package, ``extract/api.py`` needs a shared constant:

    from ..shared import BATCH_SIZE      # relative import

It works from the test suite. Then someone runs it directly —
``python pipeline/extract/api.py`` — and Python dies:

    ImportError: attempted relative import with no known parent package

Run as a SCRIPT, the file has no package context, so ``..`` means
nothing. Run as a MODULE — ``python -m pipeline.extract.api`` — the
package context exists and the relative import resolves.

Plain words: a script is a loose page; a module is a page still bound
in the book. Relative imports only make sense inside the book.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The fix is not "avoid relative imports" — it is "never run package
    files as scripts". The entry point is ALWAYS ``python -m`` from the
    project root, or a ``main.py`` / console script OUTSIDE the package.
  - ``python -m pipeline.extract.api`` sets ``__package__`` so relative
    imports resolve; ``python pipeline/extract/api.py`` leaves it empty.
  - ``sys.path`` hacks (``sys.path.insert(0, "../..")`` at the top of a
    module) are the smell: they hard-code one machine's layout and rot
    the moment the project moves.
  - Absolute imports (``from pipeline.shared import BATCH_SIZE``) read
    the same from every file in the project — grep-able, refactorable,
    and immune to "where was this file when it ran".

Your solution: ``dotted_name_for(file_path, project_root)`` converts a
file path to the dotted name ``python -m`` expects; ``run_as_module``
executes it with real module semantics; ``run_as_script`` shows the
script-execution failure. Then run the tests:
``python -m pytest tests -q`` from the day-12 folder.

ANALOGY
-------
``python -m`` is giving the courier the full labeled address
(``pipeline.extract.api``); ``python path/to/api.py`` is handing them a
loose page and saying "you know where this goes".
"""

import runpy
import sys
from pathlib import Path

SHARED_PY = 'BATCH_SIZE = 2\n'

API_PY = '''\
"""Extract stage: uses a relative import — needs package context."""
from ..shared import BATCH_SIZE

RESULT = []


def fetch():
    return ["row"] * BATCH_SIZE


if __name__ == "__main__":
    RESULT.extend(fetch())
'''


def write_demo_package(root):
    """Write a minimal package whose module uses a relative import."""
    root = Path(root)
    (root / "pipeline" / "extract").mkdir(parents=True, exist_ok=True)
    (root / "pipeline" / "__init__.py").write_text("")
    (root / "pipeline" / "extract" / "__init__.py").write_text("")
    (root / "pipeline" / "shared.py").write_text(SHARED_PY)
    api = root / "pipeline" / "extract" / "api.py"
    api.write_text(API_PY)
    return api


def dotted_name_for(file_path, project_root):
    """Convert a file path to the dotted name ``python -m`` expects.

    ``pipeline/extract/api.py`` -> ``"pipeline.extract.api"``;
    ``pipeline/__init__.py``   -> ``"pipeline"``;
    ``main.py`` (at the root)  -> ``"main"``.
    Raises ValueError when the file is outside the project root.
    """
    path = Path(file_path).resolve()
    root = Path(project_root).resolve()
    try:
        rel = path.relative_to(root)
    except ValueError:
        raise ValueError(f"{file_path} is not inside project root {project_root}")
    if path.name == "__init__.py":
        parts = rel.parent.parts
    else:
        parts = rel.with_suffix("").parts
    if not parts:
        raise ValueError(f"cannot make a dotted name from {file_path}")
    return ".".join(parts)


def run_as_module(dotted_name, project_root):
    """Run ``dotted_name`` with real module semantics (like ``python -m``).

    Returns the executed module's namespace dict.
    """
    root = str(Path(project_root).resolve())
    sys.path.insert(0, root)
    try:
        import importlib

        importlib.invalidate_caches()
        return runpy.run_module(dotted_name, run_name="__main__", alter_sys=True)
    finally:
        sys.path.remove(root)


def run_as_script(file_path):
    """Run a file as a bare script (like ``python path/to/file.py``).

    Returns the executed namespace dict — or raises, which is the point:
    relative imports have no package context here.
    """
    return runpy.run_path(str(file_path), run_name="__main__")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        api = write_demo_package(tmp)
        print("dotted name ->", dotted_name_for(api, tmp))

        try:
            run_as_script(api)
        except ImportError as exc:
            print("as script  -> ImportError:", exc)

        ns = run_as_module("pipeline.extract.api", tmp)
        print("as module  -> RESULT =", ns["RESULT"])
