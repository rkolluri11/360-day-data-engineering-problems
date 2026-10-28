"""Problem 5 — the pinned pipeline end to end: resolve, freeze, verify
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
All four earlier problems meet in one build step: take the loose
requirements a developer wrote, resolve the whole graph (Problem 4),
freeze the exact versions plus their digests into a lockfile
(Problem 3), and then verify every later machine against that
lockfile. If any step is skipped, "reproducible" is just a word.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Freeze is deterministic: the same requirements and catalog
    always produce the same lockfile text, byte for byte, so a
    lockfile diff means the environment really changed.
  - A missing digest fails the build: a locked version with no
    recorded hash cannot be verified later, so it must never be
    frozen in the first place.
  - Verification is the lockfile's own check (Problem 3): the
    pipeline never re-implements drift detection, so the report a
    developer sees is the same report the build produced.
  - Conflicts surface, they do not get papered over: an impossible
    graph raises Problem 4's ConflictError out of the build, with
    the package named, instead of freezing a partial environment.

Plain words: resolve the menu, write down exactly what was served
and its seal number, and count the bags again on arrival — the
same list, checked the same way, every time.
"""

from problem_01_version_pins import Requirement
from problem_03_lockfile_drift import LockEntry, Lockfile
from problem_04_diamond_conflict import resolve_graph


class MissingDigestError(ValueError):
    """A resolved package has no recorded artifact digest to freeze."""


def _lookup_digest(name, version, digests):
    if (name, version) in digests:
        return digests[(name, version)]
    if name in digests:
        return digests[name]
    return None


class PinnedEnvironment:
    """A resolved, frozen environment: lockfile plus its checks."""

    def __init__(self, requirements, catalog, digests):
        resolved = resolve_graph(requirements, catalog)
        entries = []
        for name in sorted(resolved):
            version = resolved[name]
            digest = _lookup_digest(name, version, digests or {})
            if digest is None:
                raise MissingDigestError(
                    f"no digest recorded for {name}=={version}")
            entries.append(LockEntry(name, version, str(digest)))
        self.resolved = resolved
        self.lockfile = Lockfile(entries)

    def freeze(self):
        """The lockfile text: the exact, deterministic build record."""
        return self.lockfile.to_text()

    def verify(self, installed):
        """Drift report for an installed set (Problem 3's check)."""
        return self.lockfile.verify(installed)

    def is_clean(self, installed):
        return self.lockfile.is_clean(installed)


def build_pinned_environment(requirements, catalog, digests):
    return PinnedEnvironment(requirements, catalog, digests)


def freeze(requirements, catalog, digests):
    """One call: resolve the graph and return the lockfile text."""
    return build_pinned_environment(requirements, catalog, digests).freeze()
