"""Day 12 tests — every solution must pass before the day is committed."""

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_split_the_monolith import exec_as, render_flat_script, render_guarded_module
from problem_02_make_it_a_package import write_package
from problem_03_absolute_imports import (
    dotted_name_for,
    run_as_module,
    run_as_script,
    write_demo_package,
)
from problem_04_freeze_the_environment import (
    build_snapshot,
    check_drift,
    find_conflicts,
    parse_requirement,
    spec_satisfied,
)
from problem_05_one_venv_per_project import resolve_import, which_env_breaks


def _clear_pipeline_modules():
    for name in [n for n in sys.modules if n == "pipeline" or n.startswith("pipeline.")]:
        del sys.modules[name]
    importlib.invalidate_caches()


# --- Problem 1: the __main__ guard --------------------------------------------


def test_01_flat_script_runs_on_import():
    ns = exec_as(render_flat_script(), "pipeline")
    assert ns["SIDE_EFFECTS"] == ["job ran at import time"]
    assert ns["ROWS"] == ["row1", "row2"]


def test_01_guarded_module_is_silent_on_import(capsys):
    ns = exec_as(render_guarded_module(), "extract")
    assert capsys.readouterr().out == ""
    assert ns["SIDE_EFFECTS"] == []
    assert callable(ns["main"])


def test_01_guarded_module_runs_as_main(capsys):
    exec_as(render_guarded_module(), "__main__")
    assert "extracted 2" in capsys.readouterr().out


def test_01_stage_reusable_without_side_effects():
    ns = exec_as(render_guarded_module(), "extract")
    assert ns["extract"]() == ["row1", "row2"]
    assert ns["SIDE_EFFECTS"] == []  # importing + calling never ran the job


# --- Problem 2: the package contract ------------------------------------------


@pytest.fixture()
def installed_package(tmp_path, monkeypatch):
    write_package(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    _clear_pipeline_modules()
    yield tmp_path
    _clear_pipeline_modules()


def test_02_from_pipeline_extract_import_run(installed_package):
    from pipeline.extract import run

    assert run("b7") == [{"batch": "b7", "n": 0}, {"batch": "b7", "n": 1}, {"batch": "b7", "n": 2}]


def test_02_star_import_respects_all(installed_package):
    ns = {}
    exec("from pipeline.extract import *", ns)
    assert "run" in ns
    assert "_parse_raw" not in ns
    assert "api" not in ns  # submodule not leaked by star import


def test_02_private_helper_not_on_package(installed_package):
    import pipeline.extract

    assert not hasattr(pipeline.extract, "_parse_raw")
    from pipeline.extract import api

    assert callable(api._parse_raw)  # still reachable where it belongs


def test_02_version_single_sourced(installed_package):
    import pipeline

    assert pipeline.VERSION == "0.1.0"
    assert pipeline.__all__ == ["extract", "load", "VERSION"]


# --- Problem 3: module vs script ----------------------------------------------


def test_03_dotted_name_for_nested_module(tmp_path):
    api = write_demo_package(tmp_path)
    assert dotted_name_for(api, tmp_path) == "pipeline.extract.api"


def test_03_dotted_name_for_init_and_top_level(tmp_path):
    write_demo_package(tmp_path)
    assert dotted_name_for(tmp_path / "pipeline" / "__init__.py", tmp_path) == "pipeline"
    main = tmp_path / "main.py"
    main.write_text("x = 1\n")
    assert dotted_name_for(main, tmp_path) == "main"


def test_03_dotted_name_outside_root_raises(tmp_path):
    with pytest.raises(ValueError):
        dotted_name_for("/etc/hostname", tmp_path)


def test_03_script_run_breaks_relative_import(tmp_path):
    api = write_demo_package(tmp_path)
    with pytest.raises(ImportError):
        run_as_script(api)


def test_03_module_run_resolves_relative_import(tmp_path):
    api = write_demo_package(tmp_path)
    _clear_pipeline_modules()
    try:
        ns = run_as_module("pipeline.extract.api", tmp_path)
    finally:
        _clear_pipeline_modules()
    assert ns["RESULT"] == ["row", "row"]
    assert dotted_name_for(api, tmp_path) == "pipeline.extract.api"


# --- Problem 4: freeze the environment ------------------------------------------


def test_04_parse_requirement_lines():
    assert parse_requirement("pandas==1.5.3") == ("pandas", "==1.5.3")
    assert parse_requirement("requests>=2.28,<3  # http client") == ("requests", ">=2.28,<3")
    assert parse_requirement("uvicorn[standard]==0.20") == ("uvicorn", "==0.20")
    assert parse_requirement("Django>=4.2; python_version < '3.13'") == ("django", ">=4.2")
    assert parse_requirement("  # just a comment") is None
    assert parse_requirement("") is None
    assert parse_requirement("-r base.txt") is None


def test_04_build_snapshot_only_pins():
    lines = ["pandas==1.5.3", "requests>=2.28", "# comment", "", "numpy==1.24.2"]
    assert build_snapshot(lines) == {"pandas": "1.5.3", "numpy": "1.24.2"}


def test_04_find_conflicts_exact_vs_range():
    assert find_conflicts(["pandas==1.5.3", "pandas>=2.0"]) == [
        ("pandas", "==1.5.3", ">=2.0")
    ]


def test_04_find_conflicts_none_when_compatible():
    assert find_conflicts(["pandas>=1.5,<3", "pandas==2.1.0"]) == []
    assert find_conflicts(["pandas==1.5.3", "pandas==1.5.3"]) == []  # dup, not conflict


def test_04_spec_satisfied_ranges():
    assert spec_satisfied(">=1.5,<3", "2.1.0")
    assert not spec_satisfied(">=1.5,<3", "3.0.0")
    assert spec_satisfied("~=1.4.2", "1.4.9")
    assert not spec_satisfied("~=1.4.2", "1.5.0")


def test_04_check_drift_the_2am_story():
    frozen = {"pandas": "1.5.3", "requests": "2.28.1"}
    installed = {"pandas": "2.1.0", "requests": "2.28.1"}
    assert check_drift(frozen, installed) == [("pandas", "1.5.3", "2.1.0")]


def test_04_check_drift_clean_and_missing():
    frozen = {"pandas": "1.5.3", "kafka-python": "1.4.7"}
    assert check_drift(frozen, {"pandas": "1.5.3"}) == [("kafka-python", "1.4.7", None)]
    assert check_drift(frozen, dict(frozen)) == []


# --- Problem 5: one venv per project --------------------------------------------


def test_05_resolve_import_first_wins():
    venv_a = "/envs/a/lib/site-packages"
    venv_b = "/envs/b/lib/site-packages"
    available = {
        (venv_a, "pandas"): venv_a + "/pandas/__init__.py",
        (venv_b, "pandas"): venv_b + "/pandas/__init__.py",
    }
    assert resolve_import("pandas", [venv_a, venv_b], available) == venv_a + "/pandas/__init__.py"
    assert resolve_import("pandas", [venv_b, venv_a], available) == venv_b + "/pandas/__init__.py"


def test_05_resolve_import_missing_returns_none():
    assert resolve_import("nope", ["/envs/a/lib/site-packages"], {}) is None


def test_05_venvs_isolate_same_module_name():
    her = "/home/her/proj/.venv/lib/site-packages"
    his = "/home/his/proj/.venv/lib/site-packages"
    available = {
        (her, "pandas"): her + "/pandas/__init__.py",
        (his, "pandas"): his + "/pandas/__init__.py",
    }
    # same code, same module name — each room resolves its own copy
    assert resolve_import("pandas", [her], available).startswith(her)
    assert resolve_import("pandas", [his], available).startswith(his)


def test_05_which_env_breaks_names_the_package():
    code_needs = {"pandas": ("<2.0", "code calls DataFrame.append, removed in pandas 2.0")}
    envs = {"hers": {"pandas": "1.5.3"}, "his": {"pandas": "2.1.0"}}
    result = which_env_breaks(code_needs, envs)
    assert set(result) == {"his"}
    pkg, installed, spec, note = result["his"][0]
    assert (pkg, installed, spec) == ("pandas", "2.1.0", "<2.0")
    assert "append" in note


def test_05_which_env_breaks_clean_and_missing():
    code_needs = {"pandas": (">=1.0", "needs DataFrame"), "kafka-python": ("==1.4.7", "client")}
    envs = {"good": {"pandas": "1.5.3", "kafka-python": "1.4.7"}, "bad": {"pandas": "1.5.3"}}
    result = which_env_breaks(code_needs, envs)
    assert set(result) == {"bad"}
    assert result["bad"][0][0] == "kafka-python"
    assert result["bad"][0][1] is None  # missing entirely
