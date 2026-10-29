"""Problem 2 — the matrix multiplies the jobs, the cache saves the time.

THE PROBLEM (beginner foothold first)
------------------------------------
One pipeline should be tested on Python 3.11 and 3.12, on Linux and
macOS. Writing four near-identical jobs is how they drift apart.
A matrix says it once — every combination of every axis becomes a
job — and a cache says: if the lockfile has not changed, do not
re-download and reinstall the world.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Matrix expansion is a cartesian product, in a deterministic
    order: axes in the order given, values in the order given. An
    empty axis is a config bug, not an empty run.
  - ``include`` adds a combination, or extends a combination it
    already matches with extra keys (e.g. an experimental flag on
    just one Python version). ``exclude`` removes every combination
    that matches all of its keys.
  - A cache key must change when anything it stands for changes:
    the OS, the Python version, or the lockfile bytes. Same inputs
    must give the same key byte for byte, or the cache is a lottery.
  - A cache store answers one question — have I seen this key? —
    and remembers what it stored, so a second identical run is a hit.

Plain words: the matrix is a multiplication table for jobs, and the
cache key is a fingerprint — change the lockfile by one byte and the
fingerprint must change, or you will test yesterday's dependencies
and call it today.
"""

import hashlib
import itertools


class MatrixError(ValueError):
    """Raised for a malformed matrix, include, or exclude entry."""


def expand_matrix(matrix):
    """Expand ``matrix`` (axis -> list of values) into combinations.

    Returns a list of dicts in deterministic order: axes in insertion
    order, values in listed order. An empty matrix gives one empty
    combination (one job, no axes). An empty axis list is an error.
    """
    if not isinstance(matrix, dict):
        raise MatrixError(f"matrix must be a mapping, got {matrix!r}")
    axes = list(matrix.keys())
    for axis in axes:
        values = matrix[axis]
        if not isinstance(values, list) or not values:
            raise MatrixError(f"matrix axis {axis!r} needs a non-empty list")
    combos = []
    for values in itertools.product(*(matrix[axis] for axis in axes)):
        combos.append(dict(zip(axes, values)))
    return combos


def apply_include_exclude(combos, include=None, exclude=None):
    """Apply GitHub-style include / exclude rules to ``combos``.

    Exclude first: drop any combination matching every key of an
    exclude entry. Then include: an entry that matches an existing
    combination on every shared key extends that combination with
    its extra keys; an entry matching nothing is appended as a new
    combination. Matching ignores keys the combination does not have
    only when the entry adds them — an entry whose axis keys conflict
    with a combination does not match it.
    """
    result = [dict(combo) for combo in combos]
    for entry in exclude or []:
        if not isinstance(entry, dict):
            raise MatrixError(f"exclude entry must be a mapping, got {entry!r}")
        result = [
            combo
            for combo in result
            if not all(combo.get(k) == v for k, v in entry.items())
        ]
    for entry in include or []:
        if not isinstance(entry, dict):
            raise MatrixError(f"include entry must be a mapping, got {entry!r}")
        matched = False
        for combo in result:
            shared = [k for k in entry if k in combo]
            if shared and all(combo[k] == entry[k] for k in shared):
                combo.update(entry)
                matched = True
        if not matched:
            result.append(dict(entry))
    return result


def cache_key(os_name, python_version, lockfile_text, extra=""):
    """Build a deterministic cache key from OS, Python, lockfile, extra.

    The lockfile content is hashed (sha256, first 16 hex chars), so a
    one-byte lockfile change changes the key while the key itself
    stays short enough for a log line.
    """
    if not os_name or not python_version:
        raise MatrixError("cache key needs an OS and a Python version")
    if not isinstance(lockfile_text, str):
        raise MatrixError("lockfile content must be text")
    fingerprint = hashlib.sha256(
        "\n".join([os_name, str(python_version), lockfile_text, str(extra)]).encode()
    ).hexdigest()[:16]
    return f"ci-{os_name}-py{python_version}-{fingerprint}"


class Cache:
    """A tiny in-memory cache store: put a key, ask if it was seen."""

    def __init__(self):
        self._keys = set()

    def put(self, key):
        self._keys.add(key)

    def contains(self, key):
        return key in self._keys

    def hit_or_store(self, key):
        """Return True on a hit; on a miss, store the key and return False."""
        if key in self._keys:
            return True
        self._keys.add(key)
        return False

    def __len__(self):
        return len(self._keys)


if __name__ == "__main__":
    combos = expand_matrix({"python": ["3.11", "3.12"], "os": ["linux"]})
    combos = apply_include_exclude(
        combos, exclude=[{"python": "3.11"}], include=[{"python": "3.12", "experimental": True}]
    )
    print(combos)
    print(cache_key("linux", "3.12", "pandas==2.0.3\n"))
