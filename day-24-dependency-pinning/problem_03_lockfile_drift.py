"""Problem 3 — the lockfile is the truth: detect drift, don't guess it
=====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Once a resolver picks versions, those choices must be written down
somewhere exact — the lockfile — and every later install must be
checked against it. Otherwise "it worked on my machine" returns:
one machine quietly has pandas 1.5.3, another has 2.0.1, and the
pipeline behaves differently on each.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Drift has four distinct shapes, and conflating them hides the
    fix: missing (in the lock, not installed), extra (installed,
    not in the lock), version drift (installed, wrong version),
    digest mismatch (right version, wrong bytes — a tampered or
    rebuilt artifact, not a version bump).
  - The lockfile format is round-trippable: ``to_text`` output
    parses back to the same entries, in sorted order, so a diff
    of two lockfiles is a diff of two environments — no noise.
  - Duplicate entries and malformed lines are rejected at parse
    time: a lockfile that silently drops a duplicate package is
    a lockfile that locks nothing.
  - Verification never raises on drift — drift is a report, not a
    crash. It raises only on a malformed lockfile or installed
    set it cannot read.

Plain words: the lockfile is the packing list, and verification is
counting the bags at the airport — missing, extra, wrong size, or
the seal broken are four different problems, and you name each.
"""

from dataclasses import dataclass

from problem_01_version_pins import PinError, Version


class LockfileError(ValueError):
    """Raised for a malformed lockfile line or duplicate entry."""


@dataclass(frozen=True)
class LockEntry:
    """One locked package: name, exact version, and artifact digest."""
    name: str
    version: str
    digest: str = ""

    def __post_init__(self):
        if not self.name or not str(self.name).strip():
            raise LockfileError("lock entry needs a non-empty name")
        try:
            Version(self.version)
        except PinError as exc:
            raise LockfileError(f"invalid locked version: {exc}") from exc
        # Normalise the name/version so "Pandas" and "1.5" compare cleanly.
        object.__setattr__(self, "name", str(self.name).strip().lower())
        object.__setattr__(self, "version", str(Version(self.version)))


@dataclass(frozen=True)
class Drift:
    """One difference between the lockfile and an installed set."""
    kind: str  # missing | extra | version_drift | digest_mismatch
    name: str
    expected: str
    actual: str


class Lockfile:
    """A sorted, duplicate-free set of locked package versions."""

    def __init__(self, entries=()):
        by_name = {}
        for entry in entries:
            if not isinstance(entry, LockEntry):
                entry = LockEntry(*entry)
            if entry.name in by_name:
                raise LockfileError(f"duplicate lock entry for {entry.name!r}")
            by_name[entry.name] = entry
        self.entries = tuple(by_name[name] for name in sorted(by_name))

    def to_text(self):
        lines = []
        for entry in self.entries:
            line = f"{entry.name}=={entry.version}"
            if entry.digest:
                line += f"  # {entry.digest}"
            lines.append(line)
        return "\n".join(lines) + ("\n" if lines else "")

    @classmethod
    def from_text(cls, text):
        entries = []
        for lineno, raw in enumerate(str(text).splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            body, _, digest = line.partition("#")
            body = body.strip()
            if "==" not in body:
                raise LockfileError(
                    f"line {lineno}: expected 'name==version', got {raw!r}")
            name, version = body.split("==", 1)
            entries.append(LockEntry(name.strip(), version.strip(),
                                     digest.strip()))
        return cls(entries)

    def verify(self, installed):
        """Compare an installed set to this lock; return a Drift list.

        ``installed`` maps a name to a version string, or to a
        ``(version, digest)`` pair. An empty list means no drift.
        """
        normalised = {}
        for name, value in installed.items():
            if isinstance(value, (tuple, list)):
                version, digest = value[0], value[1] if len(value) > 1 else ""
            else:
                version, digest = value, ""
            normalised[str(name).strip().lower()] = (
                str(Version(version)), str(digest))
        locked = {entry.name: entry for entry in self.entries}
        drifts = []
        for name in sorted(locked):
            entry = locked[name]
            if name not in normalised:
                drifts.append(Drift("missing", name,
                                    f"{entry.version} ({entry.digest})", ""))
            else:
                version, digest = normalised[name]
                if version != entry.version:
                    drifts.append(Drift("version_drift", name,
                                        entry.version, version))
                elif entry.digest and digest != entry.digest:
                    drifts.append(Drift("digest_mismatch", name,
                                        entry.digest, digest))
        for name in sorted(normalised):
            if name not in locked:
                version, digest = normalised[name]
                drifts.append(Drift("extra", name, "",
                                    f"{version} ({digest})" if digest else version))
        return drifts

    def is_clean(self, installed):
        return not self.verify(installed)
