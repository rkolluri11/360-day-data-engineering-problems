"""Day 24 tests — dependency pinning and lockfiles.

No network, no wall clock, no real packages: every catalog and
digest is a test string. Stdlib only.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_version_pins import PinError, Requirement, Specifier, Version
from problem_02_lockfile_resolution import (
    UnknownPackageError as FlatUnknown,
    UnsatisfiableError,
    resolve,
)
from problem_03_lockfile_drift import Drift, LockEntry, Lockfile, LockfileError
from problem_04_diamond_conflict import (
    ConflictError,
    UnknownPackageError,
    resolve_graph,
)
from problem_05_pinned_pipeline import (
    MissingDigestError,
    PinnedEnvironment,
    freeze,
)


# --- Problem 1: pins ---------------------------------------------------------

def test_version_compares_numerically_not_as_text():
    assert Version("1.10") > Version("1.9")
    assert Version("1.2") == Version("1.2.0")
    assert Version("2.0") > Version("1.999")


def test_range_specifiers_and_wildcard():
    assert Specifier(">=1.2").satisfies(Version("1.2"))
    assert not Specifier("<2.0").satisfies(Version("2.0"))
    assert Specifier("==1.2.*").satisfies(Version("1.2.9"))
    assert not Specifier("==1.2.*").satisfies(Version("1.3.0"))
    assert Specifier("!=1.2.*").satisfies(Version("1.3.0"))
    assert Specifier("~=1.2.3").satisfies(Version("1.2.9"))
    assert not Specifier("~=1.2.3").satisfies(Version("1.3.0"))
    assert Specifier("~=1.2").satisfies(Version("1.9"))
    assert not Specifier("~=1.2").satisfies(Version("2.0"))


def test_requirement_parses_glued_and_spaced_forms():
    assert Requirement.parse("pandas>=1.2,<2.0").satisfies(Version("1.5"))
    assert not Requirement.parse("pandas >=1.2, <2.0").satisfies(Version("2.0"))
    assert Requirement.parse("pandas").satisfies(Version("99.0"))


def test_malformed_pins_fail_loudly():
    for bad in ("1.x", "=>1.2", ">=x", "~=1", "pandas>>1.2", ""):
        with pytest.raises(PinError):
            if bad.startswith("pandas") or bad == "":
                Requirement.parse(bad)
            else:
                Specifier(bad)
    with pytest.raises(PinError):
        Version("")


# --- Problem 2: flat resolution ---------------------------------------------

CATALOG = {"pandas": ["1.2.0", "1.5.3", "2.0.1"], "numpy": ["1.24", "1.26"]}


def test_resolves_highest_satisfying_and_merges_constraints():
    assert resolve(["pandas>=1.2,<2.0"], CATALOG)["pandas"] == "1.5.3"
    assert resolve(["pandas>=1.2", "pandas<1.5"], CATALOG)["pandas"] == "1.2.0"
    assert resolve(["numpy"], CATALOG)["numpy"] == "1.26"


def test_flat_resolution_errors_name_the_problem():
    with pytest.raises(UnsatisfiableError):
        resolve(["pandas>=3.0"], CATALOG)
    with pytest.raises(FlatUnknown):
        resolve(["scipy"], CATALOG)


# --- Problem 3: lockfile drift -----------------------------------------------

LOCK = Lockfile([
    LockEntry("pandas", "1.5.3", "sha256:aaa"),
    LockEntry("numpy", "1.26", "sha256:bbb"),
])


def test_lockfile_round_trips_and_sorts():
    assert Lockfile.from_text(LOCK.to_text()).entries == LOCK.entries
    assert [e.name for e in LOCK.entries] == ["numpy", "pandas"]


def test_verify_reports_each_drift_shape_distinctly():
    drifts = {d.name: d for d in LOCK.verify({
        "pandas": ("1.5.3", "sha256:tampered"),
        "scipy": ("1.11", ""),
    })}
    assert drifts["pandas"].kind == "digest_mismatch"
    assert drifts["numpy"].kind == "missing"
    assert drifts["scipy"].kind == "extra"
    assert LOCK.is_clean({"pandas": ("1.5.3", "sha256:aaa"),
                          "numpy": ("1.26", "sha256:bbb")})


def test_version_drift_is_not_a_digest_mismatch():
    drifts = LOCK.verify({"pandas": ("2.0.1", "sha256:aaa"),
                          "numpy": ("1.26", "sha256:bbb")})
    assert [d.kind for d in drifts] == ["version_drift"]
    assert drifts[0].name == "pandas"


def test_duplicate_and_malformed_lock_lines_rejected():
    with pytest.raises(LockfileError):
        Lockfile([LockEntry("pandas", "1.0"), LockEntry("pandas", "2.0")])
    with pytest.raises(LockfileError):
        Lockfile.from_text("pandas 1.5.3\n")


# --- Problem 4: diamond conflicts --------------------------------------------

GRAPH = {
    "app": {"1.0": {"liba": ">=0.9", "libb": ">=1.0"}},
    "liba": {"1.0": {"shared": ">=2.0"}, "0.9": {"shared": ">=1.0,<2.0"}},
    "libb": {"1.0": {"shared": "<2.0"}},
    "shared": {"1.5": {}, "2.1": {}},
}


def test_backtracking_finds_the_older_parent_that_fits():
    # Greedy newest liba (1.0, shared>=2.0) clashes with libb
    # (shared<2.0); the resolver must fall back to liba 0.9.
    resolved = resolve_graph(["app"], GRAPH)
    assert resolved == {"app": "1.0", "liba": "0.9", "libb": "1.0",
                        "shared": "1.5"}


def test_impossible_diamond_is_a_named_conflict():
    bad = dict(GRAPH)
    bad["liba"] = {"1.0": {"shared": ">=2.0"}}
    with pytest.raises(ConflictError):
        resolve_graph(["app"], bad)


def test_cycle_terminates_and_unknown_is_an_error():
    cyclic = {"a": {"1.0": {"b": ">=1.0"}}, "b": {"1.0": {"a": ">=1.0"}}}
    assert resolve_graph(["a"], cyclic) == {"a": "1.0", "b": "1.0"}
    with pytest.raises(UnknownPackageError):
        resolve_graph(["nope"], GRAPH)


# --- Problem 5: pinned pipeline ----------------------------------------------

DIGESTS = {("app", "1.0"): "sha256:app", ("liba", "0.9"): "sha256:liba",
           ("libb", "1.0"): "sha256:libb", ("shared", "1.5"): "sha256:sh"}


def test_pipeline_freezes_deterministically_and_verifies():
    env = PinnedEnvironment(["app"], GRAPH, DIGESTS)
    assert env.freeze() == PinnedEnvironment(["app"], GRAPH, DIGESTS).freeze()
    assert "liba==0.9" in env.freeze() and "shared==1.5" in env.freeze()
    installed = {"app": ("1.0", "sha256:app"), "liba": ("0.9", "sha256:liba"),
                 "libb": ("1.0", "sha256:libb"), "shared": ("1.5", "sha256:sh")}
    assert env.is_clean(installed)
    assert env.verify({**installed, "shared": ("2.1", "sha256:sh")})[0].kind \
        == "version_drift"


def test_pipeline_refuses_a_missing_digest_and_a_conflict():
    with pytest.raises(MissingDigestError):
        PinnedEnvironment(["app"], GRAPH, {})
    bad = dict(GRAPH)
    bad["liba"] = {"1.0": {"shared": ">=2.0"}}
    with pytest.raises(ConflictError):
        freeze(["app"], bad, DIGESTS)
