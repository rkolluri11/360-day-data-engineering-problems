"""Problem 2 — resolve to the highest version that satisfies every pin
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A requirements file usually names ranges, not exact versions:
"pandas>=1.2,<2.0". Somebody still has to pick ONE version to
install, and two machines must pick the SAME one. The resolver is
that somebody: given every available version and every constraint
on a package, it picks the highest version all constraints allow.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Constraints merge: two requirements for one package ("pandas
    >=1.2" and "pandas<1.5") both bind — the winner must satisfy
    both, not just the last one seen.
  - Highest wins, not first listed: the catalog may arrive in any
    order, so the resolver sorts by version, never by list order.
  - An unknown package is an error, not an empty result: silently
    skipping a package the catalog never heard of ships a broken
    environment that only fails at import time.
  - An unsatisfiable pin is an error with the package named: the
    operator needs to know WHICH pin cannot be met, not just that
    resolution failed somewhere.

Plain words: the resolver is the bouncer with the guest list — it
lets in the newest guest every rule allows, and it says out loud
when the list names nobody at all.
"""

from problem_01_version_pins import Requirement, Version


class UnknownPackageError(ValueError):
    """The catalog has no versions at all for a required package."""


class UnsatisfiableError(ValueError):
    """No catalog version satisfies every constraint on a package."""


def _as_requirement(value):
    if isinstance(value, Requirement):
        return value
    return Requirement.parse(value)


def resolve(requirements, catalog):
    """Resolve direct requirements to one version string per package.

    ``catalog`` maps a package name to an iterable of version
    strings (any order). Returns ``{name: version_string}`` with
    the highest version satisfying every constraint on that name.
    """
    catalog = {str(name).lower(): list(versions)
               for name, versions in catalog.items()}
    constraints = {}
    for raw in requirements:
        req = _as_requirement(raw)
        constraints.setdefault(req.name, []).extend(req.specifiers)

    resolved = {}
    for name in sorted(constraints):
        if name not in catalog:
            raise UnknownPackageError(f"no versions in catalog for {name!r}")
        candidates = []
        for raw_version in catalog[name]:
            version = Version(raw_version)
            if all(spec.satisfies(version) for spec in constraints[name]):
                candidates.append(version)
        if not candidates:
            specs = ",".join(str(s) for s in constraints[name])
            raise UnsatisfiableError(
                f"no version of {name!r} satisfies {specs!r}")
        resolved[name] = str(max(candidates))
    return resolved
