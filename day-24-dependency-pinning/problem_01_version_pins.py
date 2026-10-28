"""Problem 1 — a pin is a contract, not a wish: exact versions and ranges
========================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
"Install pandas" on two machines on two different days can install
two different pandas versions — and a pipeline that passed on Monday
fails on Tuesday with no code change at all. A pin stops that drift:
it names exactly which version is allowed, in a form a machine can
check, not a comment a human might ignore.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A version is a dotted number, compared numerically: 1.10 is
    NEWER than 1.9, even though the string "1.9" sorts after
    "1.10". String comparison is the classic pin bug.
  - A specifier is one operator plus one version, and several can
    be ANDed with commas: ">=1.2,<2.0" means both must hold.
  - "==" can carry a wildcard prefix: "==1.2.*" pins a whole
    patch family, not one release. "!=" negates it the same way.
  - "~=" is the compatible-release operator: "~=1.2.3" means
    ">=1.2.3, ==1.2.*"; "~=1.2" means ">=1.2, ==1.*". It needs at
    least two version segments, or it says nothing precise.
  - Malformed pins fail at parse time, loudly: a bad pin that is
    silently ignored is worse than no pin at all.

Plain words: a pin is a hotel reservation with a room number, not
"somewhere nice" — if the number does not match, you do not check in.
"""

import re

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SPEC_RE = re.compile(r"^(==|!=|>=|<=|~=|>|<)\s*(\d+(?:\.\d+)*(?:\.\*)?)$")


class PinError(ValueError):
    """Raised for a malformed version, specifier, or requirement."""


def _pad(parts, length):
    return tuple(parts) + (0,) * (length - len(parts))


class Version:
    """A dotted numeric version, compared numerically, not as text."""

    def __init__(self, text):
        if not isinstance(text, str) or not text.strip():
            raise PinError("version must be a non-empty string")
        text = text.strip()
        segments = text.split(".")
        if any(not seg.isdigit() for seg in segments):
            raise PinError(f"invalid version {text!r}: segments must be numbers")
        self.parts = tuple(int(seg) for seg in segments)

    def _key(self, other):
        length = max(len(self.parts), len(other.parts))
        return _pad(self.parts, length), _pad(other.parts, length)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        mine, theirs = self._key(other)
        return mine == theirs

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        mine, theirs = self._key(other)
        return mine < theirs

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        return not self <= other

    def __ge__(self, other):
        return not self < other

    def __hash__(self):
        # 1.2 and 1.2.0 are the same version, so hash the trimmed form.
        parts = self.parts
        while len(parts) > 1 and parts[-1] == 0:
            parts = parts[:-1]
        return hash(parts)

    def __str__(self):
        return ".".join(str(part) for part in self.parts)

    def __repr__(self):
        return f"Version({str(self)!r})"


class Specifier:
    """One operator plus one version, e.g. ">=1.2" or "==1.2.*"."""

    def __init__(self, text):
        if not isinstance(text, str):
            raise PinError("specifier must be a string")
        match = _SPEC_RE.match(text.strip())
        if not match:
            raise PinError(f"invalid specifier {text!r}")
        self.operator, raw = match.groups()
        self.is_wildcard = raw.endswith(".*")
        if self.is_wildcard and self.operator not in ("==", "!="):
            raise PinError(f"wildcard only allowed with == / !=, got {text!r}")
        self.version_text = raw[:-2] if self.is_wildcard else raw
        self.version = Version(self.version_text)
        if self.operator == "~=" and len(self.version.parts) < 2:
            raise PinError(f"~= needs at least two segments, got {text!r}")

    def _prefix(self):
        return self.version.parts

    def satisfies(self, version):
        if not isinstance(version, Version):
            version = Version(version)
        op, mine = self.operator, version
        if self.is_wildcard:
            prefix = self._prefix()
            matched = _pad(mine.parts, len(prefix))[: len(prefix)] == prefix \
                if len(mine.parts) >= len(prefix) else False
            # A shorter version matches only if its padded form equals
            # the prefix, e.g. 1.2 matches 1.2.* but 1.3 does not.
            if len(mine.parts) < len(prefix):
                matched = _pad(mine.parts, len(prefix)) == prefix
            return matched if op == "==" else not matched
        if op == "==":
            return mine == self.version
        if op == "!=":
            return mine != self.version
        if op == ">=":
            return mine >= self.version
        if op == "<=":
            return mine <= self.version
        if op == ">":
            return mine > self.version
        if op == "<":
            return mine < self.version
        if op == "~=":
            # >= base, and same prefix except the last segment.
            upper_parts = list(self.version.parts[:-1])
            upper_parts[-1] += 1
            upper = Version(".".join(str(p) for p in upper_parts))
            prefix = self.version.parts[:-1]
            padded = _pad(mine.parts, len(prefix))
            return mine >= self.version and padded[: len(prefix)] == prefix \
                and mine < upper
        raise PinError(f"unknown operator {op!r}")

    def __str__(self):
        suffix = ".*" if self.is_wildcard else ""
        return f"{self.operator}{self.version_text}{suffix}"

    def __repr__(self):
        return f"Specifier({str(self)!r})"


def parse_specifiers(text):
    """Parse a comma-separated specifier list; "" means any version."""
    if text is None or not str(text).strip():
        return []
    return [Specifier(part) for part in str(text).split(",") if part.strip()]


class Requirement:
    """A package name plus its specifiers, e.g. "pandas>=1.2,<2.0"."""

    def __init__(self, name, specifiers=()):
        if not isinstance(name, str) or not _NAME_RE.match(name.strip()):
            raise PinError(f"invalid package name {name!r}")
        self.name = name.strip().lower()
        if isinstance(specifiers, str):
            specifiers = parse_specifiers(specifiers)
        self.specifiers = list(specifiers)

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str) or not text.strip():
            raise PinError("requirement must be a non-empty string")
        text = text.strip()
        parts = text.split(None, 1)
        name = parts[0]
        # A name may be glued to its first specifier: "pandas>=1.2".
        glued = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(.*)$", name)
        if glued and glued.group(2):
            name, rest = glued.groups()
            spec_text = rest + (" " + parts[1] if len(parts) > 1 else "")
        else:
            spec_text = parts[1] if len(parts) > 1 else ""
        return cls(name, parse_specifiers(spec_text.replace(" ", "")))

    def satisfies(self, version):
        return all(spec.satisfies(version) for spec in self.specifiers)

    def __str__(self):
        specs = ",".join(str(s) for s in self.specifiers)
        return self.name + specs

    def __repr__(self):
        return f"Requirement({str(self)!r})"
