"""Problem 5 — one venv per project: same code, different rooms
==================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Two engineers install the same pipeline. Same laptop, same week. Hers
runs. His dies on an import error. Same code — different environments:
her venv has pandas 1.5.3, his has 2.1.0, and the code calls
``DataFrame.append`` — removed in pandas 2.0.

``python -m venv .venv`` gives each project its OWN room: its own
interpreter link, its own ``site-packages``, its own pip. Two pandas
versions stop fighting because they never meet.

Plain words: a virtualenv is the room the labeled box unpacks into —
same boxes, same room, every time.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Import resolution is FIRST-WINS over ``sys.path``: the first
    directory on the path that contains the module wins. A stray
    ``.pth`` file, a ``PYTHONPATH`` leftover, or a globally installed
    copy can shadow the venv's package — "but I pip-installed it!"
  - Venvs are cheap and disposable; debugging a polluted global
    interpreter is not. One venv per project, created from the
    requirements file, deleted and rebuilt rather than repaired.
  - ``pip freeze`` INSIDE the activated venv is the truth about that
    room — freeze outside it and you photograph the wrong room.
  - The diagnosis that matters: given each environment's package list
    and what the CODE actually requires, name the exact package whose
    version breaks the build — before the 2 AM page does.

Your solution: ``resolve_import`` (first-wins ``sys.path`` lookup over
a fake filesystem) and ``which_env_breaks`` (the post's hook, as a
function: which environment dies on which requirement). Then run the
tests: ``python -m pytest tests -q`` from the day-12 folder.

ANALOGY
-------
``sys.path`` is the order the movers check rooms for a labeled box:
the first room that has it wins — even if a newer box sits in a room
further down the hall.
"""

import re


def resolve_import(dotted_name, search_path, available):
    """First-wins import resolution over ``search_path``.

    ``available`` maps ``(directory, dotted_name)`` -> file path, a fake
    of what each directory on ``sys.path`` contains. Returns the winning
    file path, or None when no directory provides the module.
    """
    for entry in search_path:
        hit = available.get((entry, dotted_name))
        if hit is not None:
            return hit
    return None


_SPEC = re.compile(r"(==|>=|<=|~=|!=|>|<)\s*([0-9][0-9A-Za-z.]*)")


def _vkey(version):
    parts = []
    for chunk in str(version).split("."):
        m = re.match(r"\d+", chunk)
        parts.append(int(m.group()) if m else 0)
    return tuple(parts)


def _pad(a, b):
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)), b + (0,) * (n - len(b))


def _spec_ok(spec, version):
    """True when ``version`` satisfies the comma-separated ``spec``."""
    for part in str(spec).split(","):
        m = re.fullmatch(r"(==|>=|<=|~=|!=|>|<)\s*([0-9][0-9A-Za-z.]*)", part.strip())
        if not m:
            raise ValueError(f"unparseable specifier: {spec!r}")
        op, want = m.group(1), m.group(2)
        v, w = _pad(_vkey(version), _vkey(want))
        ok = {
            "==": v == w,
            "!=": v != w,
            ">=": v >= w,
            "<=": v <= w,
            ">": v > w,
            "<": v < w,
            "~=": v >= w and v[: len(w) - 1] == w[: len(w) - 1],
        }[op]
        if not ok:
            return False
    return True


def which_env_breaks(code_requirements, environments):
    """Name the exact package version that breaks each environment.

    ``code_requirements``: ``{package: (spec, note)}`` — what the code
    needs and WHY (e.g. which API the code calls).
    ``environments``: ``{env_name: {package: installed_version}}``.

    Returns ``{env_name: [(package, installed, spec, note), ...]}`` for
    environments violating at least one requirement; clean environments
    are absent from the result.
    """
    broken = {}
    for env_name, installed in environments.items():
        problems = []
        for package, (spec, note) in code_requirements.items():
            version = installed.get(package)
            if version is None or not _spec_ok(spec, version):
                problems.append((package, version, spec, note))
        if problems:
            broken[env_name] = problems
    return broken


if __name__ == "__main__":
    # Two venvs, same module name, different rooms.
    venv_her = "/home/her/proj/.venv/lib/site-packages"
    venv_his = "/home/his/proj/.venv/lib/site-packages"
    available = {
        (venv_her, "pandas"): venv_her + "/pandas/__init__.py",  # 1.5.3
        (venv_his, "pandas"): venv_his + "/pandas/__init__.py",  # 2.1.0
    }
    print("her import resolves to ->", resolve_import("pandas", [venv_her], available))
    print("his import resolves to ->", resolve_import("pandas", [venv_his], available))

    # The post's hook, as a function call.
    code_needs = {
        "pandas": ("<2.0", "code calls DataFrame.append, removed in pandas 2.0"),
    }
    envs = {"hers": {"pandas": "1.5.3"}, "his": {"pandas": "2.1.0"}}
    print("who breaks ->", which_env_breaks(code_needs, envs))
