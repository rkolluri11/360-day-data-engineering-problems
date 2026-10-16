"""Problem 2 — make it a package: __init__.py is the public contract
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Three loose files — ``extract.py``, ``transform.py``, ``load.py`` — sit
in a folder. A teammate writes ``from pipeline.extract import run``
and gets ``ModuleNotFoundError: No module named 'pipeline'``. Files in
a folder are not a package; a folder with ``__init__.py`` is.

Plain words: ``__init__.py`` is the label on the moving box — without
it, Python sees a pile of cardboard, not a box it can pick up.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``__init__.py`` runs on first import of the package. It is where
    the package declares its PUBLIC surface: re-export the functions
    callers should use, keep helpers private to their submodule.
  - ``__all__`` controls ``from package import *``. Without it, star
    imports drag in every public name — including submodules and
    anything the ``__init__`` happened to import.
  - A private helper (``_parse_raw``) must stay reachable to its own
    module but invisible on the package: ``hasattr(pkg, "_parse_raw")``
    is False even though ``pkg.submodule._parse_raw`` exists.
  - The version lives in ONE place (``pipeline/__init__.py``), so
    ``pip show`` and the code can never disagree about what is running.

Your solution: ``write_package(root)`` builds the tree below under
``root`` — package, subpackages, and ``__init__.py`` files that form
one public contract. Then run the tests: ``python -m pytest tests -q``
from the day-12 folder.

    root/
      pipeline/
        __init__.py            # __all__ = ["extract", "load", "VERSION"]
        extract/
          __init__.py          # from pipeline.extract.api import run
          api.py               # def run(batch_id); def _parse_raw(...)
        load/
          __init__.py          # from pipeline.load.warehouse import run
          warehouse.py         # def run(rows)

ANALOGY
-------
``__init__.py`` is the inventory sticker on the moving box: it lists
exactly what is inside (``__all__``) so nobody has to open every flap.
"""

from pathlib import Path

PIPELINE_INIT = '''\
"""The pipeline package: stage packages behind one public contract."""
__all__ = ["extract", "load", "VERSION"]

VERSION = "0.1.0"
'''

EXTRACT_INIT = '''\
"""The extract stage: one public entry point."""
from pipeline.extract.api import run

__all__ = ["run"]
'''

EXTRACT_API = '''\
"""Extract stage implementation."""


def run(batch_id):
    """Fetch one batch from the source. The public entry point."""
    raw = _fetch_raw(batch_id)
    return _parse_raw(raw)


def _fetch_raw(batch_id):
    return [{"id": batch_id, "row": i} for i in range(3)]


def _parse_raw(payload):
    """Private: normalize the vendor payload. Not part of the contract."""
    return [{"batch": r["id"], "n": r["row"]} for r in payload]
'''

LOAD_INIT = '''\
"""The load stage: one public entry point."""
from pipeline.load.warehouse import run

__all__ = ["run"]
'''

LOAD_WAREHOUSE = '''\
"""Load stage implementation."""

WRITTEN = []


def run(rows):
    """Write rows to the warehouse. The public entry point."""
    WRITTEN.append(list(rows))
    return len(rows)
'''

# relative path -> file content
PACKAGE_TREE = {
    "pipeline/__init__.py": PIPELINE_INIT,
    "pipeline/extract/__init__.py": EXTRACT_INIT,
    "pipeline/extract/api.py": EXTRACT_API,
    "pipeline/load/__init__.py": LOAD_INIT,
    "pipeline/load/warehouse.py": LOAD_WAREHOUSE,
}


def write_package(root):
    """Write the package tree under ``root``. Returns the package dir."""
    root = Path(root)
    for rel, content in PACKAGE_TREE.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return root / "pipeline"


if __name__ == "__main__":
    import sys
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pkg = write_package(tmp)
        sys.path.insert(0, tmp)
        try:
            from pipeline.extract import run  # the post's import line

            print("from pipeline.extract import run ->", run("b7"))
            import pipeline

            print("pipeline.VERSION ->", pipeline.VERSION)
            print("pipeline.__all__ ->", pipeline.__all__)
        finally:
            sys.path.remove(tmp)
