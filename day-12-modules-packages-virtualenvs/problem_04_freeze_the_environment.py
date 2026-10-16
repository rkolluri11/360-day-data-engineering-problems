"""Problem 4 — freeze the environment: requirements.txt is a document
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A job moved machines with no ``requirements.txt``. ``pip install`` pulled
whatever was newest, and the load stage died at 2:04 AM on a changed
vendor API. The code was fine. The environment wasn't.

``pip freeze > requirements.txt`` turns the environment into a
rebuildable DOCUMENT: name, pinned version, one per line. Commit it, and
"it worked on my machine" becomes "it works on every machine".

Plain words: requirements.txt is the recipe card taped inside the
moving box — same ingredients, same dish, every kitchen.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Unpinned requirements (``pandas``) are a time bomb: today's install
    and next month's install are different software. Pin with ``==``.
  - The same package pinned TWICE with incompatible specifiers
    (``pandas==1.5.3`` and ``pandas>=2.0``) is a conflict pip will only
    reveal at install time — detect it in code review, not at 2 AM.
  - Comments, blank lines, ``-r`` includes, extras (``uvicorn[standard]``)
    and environment markers (``; python_version < "3.10"``) must all
    parse without choking the checker.
  - Drift check: compare the FROZEN snapshot against what is actually
    INSTALLED. Any difference is a deploy that is not what you tested.

Your solution: ``parse_requirement`` (one line -> ``(name, spec)``),
``build_snapshot`` (frozen lines -> ``{name: version}``),
``find_conflicts`` (same package, unsatisfiable specifiers), and
``check_drift`` (frozen vs installed). Then run the tests:
``python -m pytest tests -q`` from the day-12 folder.

ANALOGY
-------
``pip freeze`` is photographing the packed box before the movers come:
if anything arrives different, you can point at the photo.
"""

import re

_SPEC_PART = re.compile(r"\s*(==|>=|<=|~=|!=|>|<)\s*([0-9][0-9A-Za-z.]*)")
_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(.*?)\s*$")


def _vkey(version):
    """'2.1.0' -> (2, 1, 0); non-numeric chunks count as 0.

    Accepts a version tuple already (boundary probes pass tuples).
    """
    if isinstance(version, tuple):
        return tuple(int(x) for x in version)
    parts = []
    for chunk in str(version).split("."):
        m = re.match(r"\d+", chunk)
        parts.append(int(m.group()) if m else 0)
    return tuple(parts)


def _pad(a, b):
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)), b + (0,) * (n - len(b))


def _satisfies_one(op, want, version):
    v, w = _pad(_vkey(version), _vkey(want))
    if op == "==":
        return v == w
    if op == "!=":
        return v != w
    if op == ">=":
        return v >= w
    if op == "<=":
        return v <= w
    if op == ">":
        return v > w
    if op == "<":
        return v < w
    if op == "~=":  # compatible release: >= want, same prefix minus last part
        return v >= w and v[: len(w) - 1] == w[: len(w) - 1]
    raise ValueError(f"unknown operator {op!r}")


def spec_satisfied(spec, version):
    """True when ``version`` satisfies every comma-separated part of ``spec``."""
    checks = []
    for part in str(spec).split(","):
        m = re.fullmatch(r"(==|>=|<=|~=|!=|>|<)\s*([0-9][0-9A-Za-z.]*)", part.strip())
        if not m:
            raise ValueError(f"unparseable specifier: {spec!r}")
        checks.append((m.group(1), m.group(2)))
    return all(_satisfies_one(op, want, version) for op, want in checks)


def parse_requirement(line):
    """Parse one requirements line -> ``(name, spec)`` or None.

    Returns None for blanks and comments. Strips extras
    (``uvicorn[standard]`` -> ``uvicorn``) and environment markers.
    """
    line = line.split("#", 1)[0].split(";", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    m = _REQ_LINE.match(line)
    if not m:
        return None
    name, spec = m.group(1).lower(), m.group(2).strip()
    if spec.startswith("@"):  # direct URL reference: keep, but not a spec
        return (name, spec)
    return (name, spec)


def build_snapshot(lines):
    """Frozen lines -> ``{name: version}`` for every ``==`` pin."""
    snapshot = {}
    for line in lines:
        parsed = parse_requirement(line)
        if not parsed:
            continue
        name, spec = parsed
        m = re.fullmatch(r"\s*==\s*([0-9][0-9A-Za-z.]*)\s*", spec)
        if m:
            snapshot[name] = m.group(1)
    return snapshot


def _candidates(spec):
    """Version tuples that could plausibly satisfy ``spec`` (boundary probes)."""
    cands = set()
    for op, want in _SPEC_PART.findall(spec):
        w = _vkey(want)
        if op in ("==", ">=", "<=", "!=", "~="):
            cands.add(w)
        elif op == ">":
            cands.add(w[:-1] + (w[-1] + 1,) if w else (1,))
        elif op == "<":
            last = w[-1] - 1 if w and w[-1] > 0 else 0
            cands.add(w[:-1] + (last,) if w else (0,))
    return cands


def _specs_compatible(a, b):
    """True when some version satisfies both specifier strings."""
    for cand in _candidates(a) | _candidates(b):
        try:
            if spec_satisfied(a, cand) and spec_satisfied(b, cand):
                return True
        except ValueError:
            continue
    return False


def find_conflicts(lines):
    """Find one package pinned with mutually unsatisfiable specifiers.

    Returns ``[(name, spec_a, spec_b), ...]`` — the conflicts pip would
    only reveal at install time.
    """
    by_name = {}
    for line in lines:
        parsed = parse_requirement(line)
        if not parsed:
            continue
        name, spec = parsed
        if not spec or spec.startswith("@"):
            continue
        specs = by_name.setdefault(name, [])
        if spec not in specs:
            specs.append(spec)
    conflicts = []
    for name, specs in by_name.items():
        for i in range(len(specs)):
            for j in range(i + 1, len(specs)):
                if not _specs_compatible(specs[i], specs[j]):
                    conflicts.append((name, specs[i], specs[j]))
    return conflicts


def check_drift(frozen, installed):
    """Compare the frozen snapshot against what is actually installed.

    Returns ``[(name, frozen_version, installed_version), ...]``;
    ``installed_version`` is None when the package is missing entirely.
    Empty list means the deploy matches what was tested.
    """
    drift = []
    for name in sorted(set(frozen) | set(installed)):
        f, i = frozen.get(name), installed.get(name)
        if f != i:
            drift.append((name, f, i))
    return drift


if __name__ == "__main__":
    frozen_lines = [
        "pandas==1.5.3",
        "requests==2.28.1  # http client",
        "",
        "# pinned 2026-10-15",
    ]
    frozen = build_snapshot(frozen_lines)
    print("frozen snapshot ->", frozen)

    # the 2 AM story: the new machine installed whatever was newest
    installed = {"pandas": "2.1.0", "requests": "2.28.1"}
    print("drift vs installed ->", check_drift(frozen, installed))

    print(
        "conflicts ->",
        find_conflicts(["pandas==1.5.3", "pandas>=2.0", "requests>=2.0"]),
    )
