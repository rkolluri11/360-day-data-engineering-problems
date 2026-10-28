"""Problem 4 — the diamond: two parents, one child, incompatible pins
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Package A needs C>=2.0 and package B needs C<2.0. Both A and B are
fine on their own — together they cannot both be satisfied, and
there is no version of C that makes both parents happy. That shape
is a diamond (A and B share the child C), and it is the most common
reason a "simple" install fails with a wall of resolver output.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Constraints accumulate across the whole graph, not per parent:
    the child must satisfy every parent's pin at once, and the
    resolver must try other versions of the parents before giving
    up — a parent's older release may pin the child more loosely.
  - Backtracking is required: a greedy "newest of everything"
    picks a parent version whose child pin is impossible, then
    wrongly reports failure instead of trying the parent's next
    version down.
  - Cycles terminate: A depends on B, B depends on A. Once both
    are chosen, their pins are checked, not re-expanded forever.
  - An unknown package anywhere in the graph is an error, and an
    impossible graph is a Conflict naming the package — never a
    silent partial install.

Plain words: two parents arguing over one child's bedtime cannot
both win — the resolver tries every bedtime both accept, and if
there is none, it says so and names the child.
"""

from problem_01_version_pins import (
    PinError, Requirement, Specifier, Version, parse_specifiers,
)


class ConflictError(ValueError):
    """No version assignment satisfies every constraint in the graph."""


class UnknownPackageError(ValueError):
    """The catalog has no versions at all for a required package."""


def _as_requirement(value):
    if isinstance(value, Requirement):
        return value
    return Requirement.parse(value)


def _normalise_catalog(catalog):
    """Catalog: {name: {version: {dep_name: spec_text}}} -> typed form."""
    typed = {}
    for name, versions in catalog.items():
        name = str(name).lower()
        typed_versions = {}
        for version_text, deps in versions.items():
            version = Version(version_text)
            typed_deps = {}
            for dep_name, spec_text in (deps or {}).items():
                if isinstance(spec_text, str):
                    specs = parse_specifiers(spec_text.replace(" ", ""))
                else:
                    specs = [Specifier(s) if isinstance(s, str) else s
                             for s in spec_text]
                typed_deps[str(dep_name).lower()] = specs
            typed_versions[version] = (str(version), typed_deps)
        typed[name] = typed_versions
    return typed


def resolve_graph(requirements, catalog):
    """Resolve a full dependency graph to one version per package.

    Backtracking search: try versions newest-first, and when a
    choice makes a child unsatisfiable, backtrack to the next
    version of its parent instead of failing outright.
    """
    typed = _normalise_catalog(catalog)
    initial = {}
    for raw in requirements:
        req = _as_requirement(raw)
        initial.setdefault(req.name, []).extend(req.specifiers)

    def search(chosen, constraints):
        pending = [name for name in constraints if name not in chosen]
        if not pending:
            return chosen
        name = sorted(pending)[0]
        if name not in typed:
            raise UnknownPackageError(
                f"no versions in catalog for {name!r}")
        specs = constraints[name]
        candidates = sorted(
            (v for v in typed[name] if all(s.satisfies(v) for s in specs)),
            reverse=True)
        for version in candidates:
            _, deps = typed[name][version]
            new_chosen = dict(chosen)
            new_chosen[name] = version
            new_constraints = {k: list(v) for k, v in constraints.items()}
            usable = True
            for dep_name, dep_specs in deps.items():
                if dep_name not in typed:
                    raise UnknownPackageError(
                        f"no versions in catalog for {dep_name!r}")
                if dep_name in new_chosen:
                    if not all(s.satisfies(new_chosen[dep_name])
                               for s in dep_specs):
                        usable = False
                        break
                else:
                    new_constraints.setdefault(dep_name, []).extend(dep_specs)
            if not usable:
                continue
            result = search(new_chosen, new_constraints)
            if result is not None:
                return result
        return None

    try:
        result = search({}, initial)
    except PinError:
        raise
    if result is None:
        names = ", ".join(sorted(initial))
        raise ConflictError(
            f"no version assignment satisfies the graph for: {names}")
    return {name: str(version) for name, version in sorted(result.items())}
