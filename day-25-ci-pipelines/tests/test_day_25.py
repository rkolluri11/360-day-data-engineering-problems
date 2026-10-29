"""Day 25 tests — CI for Python pipelines in GitHub Actions.

No network, no wall clock, no real runners: every workflow, matrix,
secret, and step outcome is a test value. Stdlib only.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_workflow_model import Step, Workflow, WorkflowError, validate_cron
from problem_02_matrix_and_cache import (
    Cache,
    MatrixError,
    apply_include_exclude,
    cache_key,
    expand_matrix,
)
from problem_03_secrets_and_env import (
    EnvError,
    SecretStore,
    log_safe_env,
    mask_text,
    resolve_env,
)
from problem_04_pipeline_gates import (
    GateError,
    effective_statuses,
    gate_verdict,
    order_jobs,
)
from problem_05_ci_pipeline import run_pipeline


def _workflow(**jobs):
    return {"name": "pipeline-ci", "on": ["push"], "jobs": jobs}


def _job(*steps, **extra):
    job = {"runs-on": "ubuntu-latest", "steps": list(steps)}
    job.update(extra)
    return job


# --- Problem 1: workflow validation ----------------------------------------

def test_cron_validation():
    assert validate_cron("0 2 * * *")
    assert validate_cron("*/15 * * * *")
    assert validate_cron("0 0 1-5 * 1,3")
    assert not validate_cron("0 2 * *")  # only four fields
    assert not validate_cron("61 2 * * *")  # no 61st minute
    assert not validate_cron("0 25 * * *")  # no 25th hour
    assert not validate_cron("0 2 * * 8")  # day-of-week tops out at 7


def test_valid_workflow_with_schedule_parses():
    wf = Workflow.from_dict(
        {
            "name": "nightly",
            "on": {"push": {}, "schedule": [{"cron": "0 2 * * *"}]},
            "jobs": {"test": _job({"name": "Run tests", "run": "pytest -q"})},
        }
    )
    assert wf.summary() == {
        "name": "nightly",
        "triggers": ["push", "schedule"],
        "jobs": 1,
        "steps": 1,
    }


def test_step_needs_exactly_one_of_run_or_uses():
    with pytest.raises(WorkflowError):
        Step.from_dict({"name": "Empty"})
    with pytest.raises(WorkflowError):
        Step.from_dict({"name": "Both", "run": "pytest", "uses": "actions/checkout@v4"})


def test_uses_must_pin_a_version():
    with pytest.raises(WorkflowError):
        Step.from_dict({"name": "Checkout", "uses": "actions/checkout"})
    Step.from_dict({"name": "Checkout", "uses": "actions/checkout@v4"})


def test_job_needs_must_exist_and_job_must_have_steps():
    with pytest.raises(WorkflowError):
        Workflow.from_dict(_workflow(test=_job({"name": "T", "run": "pytest"}, needs=["ghost"])))
    with pytest.raises(WorkflowError):
        Workflow.from_dict(_workflow(empty={"runs-on": "ubuntu-latest", "steps": []}))
    with pytest.raises(WorkflowError):
        Workflow.from_dict(_workflow(a=_job({"name": "T", "run": "x"}, needs=["a"])))


def test_unknown_triggers_and_empty_trigger_list_rejected():
    with pytest.raises(WorkflowError):
        Workflow.from_dict({"name": "w", "on": ["carrier-pigeon"], "jobs": {}})
    with pytest.raises(WorkflowError):
        Workflow.from_dict({"name": "w", "on": [], "jobs": {"a": _job({"name": "T", "run": "x"})}})


# --- Problem 2: matrix and cache -------------------------------------------

def test_matrix_expands_in_deterministic_order():
    combos = expand_matrix({"python": ["3.11", "3.12"], "os": ["linux", "macos"]})
    assert combos == [
        {"python": "3.11", "os": "linux"},
        {"python": "3.11", "os": "macos"},
        {"python": "3.12", "os": "linux"},
        {"python": "3.12", "os": "macos"},
    ]


def test_matrix_empty_axis_is_an_error_and_empty_matrix_is_one_job():
    assert expand_matrix({}) == [{}]
    with pytest.raises(MatrixError):
        expand_matrix({"python": []})


def test_include_extends_and_exclude_removes():
    combos = expand_matrix({"python": ["3.11", "3.12"]})
    result = apply_include_exclude(
        combos,
        include=[{"python": "3.12", "experimental": True}, {"python": "3.13"}],
        exclude=[{"python": "3.11"}],
    )
    assert result == [
        {"python": "3.12", "experimental": True},
        {"python": "3.13"},
    ]


def test_cache_key_changes_with_lockfile_os_or_python():
    base = cache_key("ubuntu-latest", "3.12", "pandas==2.0.3\n")
    assert cache_key("ubuntu-latest", "3.12", "pandas==2.0.3\n") == base
    assert cache_key("ubuntu-latest", "3.12", "pandas==2.1.0\n") != base
    assert cache_key("macos-latest", "3.12", "pandas==2.0.3\n") != base
    assert cache_key("ubuntu-latest", "3.11", "pandas==2.0.3\n") != base


def test_cache_first_run_misses_second_hits():
    cache = Cache()
    assert cache.hit_or_store("k1") is False
    assert cache.hit_or_store("k1") is True
    assert cache.contains("k1") and not cache.contains("k2")


# --- Problem 3: secrets and env ---------------------------------------------

def test_masking_is_longest_first_and_ignores_empty():
    assert mask_text("token abcdef", ["abc", "abcdef"]) == "token ***"
    assert mask_text("nothing here", ["", "zzz"]) == "nothing here"
    assert mask_text("a s3cret b s3cret", ["s3cret"]) == "a *** b ***"


def test_env_precedence_is_step_over_job_over_workflow():
    merged = resolve_env(
        {"DB": "prod", "SHARED": "w"},
        {"DB": "staging"},
        {"RETRIES": "3"},
    )
    assert merged == {"DB": "staging", "SHARED": "w", "RETRIES": "3"}
    with pytest.raises(EnvError):
        resolve_env({"1BAD": "x"})


def test_secret_store_never_prints_values():
    store = SecretStore({"DB_PASSWORD": "s3cret-123"})
    assert "s3cret-123" not in repr(store)
    assert store.names() == ["DB_PASSWORD"]
    assert store.mask("pw=s3cret-123") == "pw=***"
    assert log_safe_env({"DB_PASSWORD": "s3cret-123", "DB": "prod"}, ["DB_PASSWORD"]) == {
        "DB_PASSWORD": "***",
        "DB": "prod",
    }


# --- Problem 4: gates ---------------------------------------------------------

def test_topological_order_and_cycle_detection():
    needs = {"lint": [], "test": ["lint"], "deploy": ["test"], "notify": ["deploy"]}
    order = order_jobs(needs)
    assert order.index("lint") < order.index("test") < order.index("deploy")
    with pytest.raises(GateError):
        order_jobs({"a": ["b"], "b": ["a"]})
    with pytest.raises(GateError):
        order_jobs({"a": ["ghost"]})


def test_effective_status_conditions():
    needs = {"test": [], "deploy": ["test"], "notify": ["deploy"]}
    eff = effective_statuses(
        needs,
        {"test": "success", "deploy": "failure"},
        {"notify": "always"},
    )
    assert eff == {"test": "success", "deploy": "failure", "notify": "success"}
    # Default condition: a dependent of a failure is skipped.
    eff2 = effective_statuses(needs, {"test": "failure"})
    assert eff2["deploy"] == "skipped" and eff2["notify"] == "skipped"
    # Failure condition: runs only when a need failed.
    eff3 = effective_statuses(
        {"test": [], "alert": ["test"]},
        {"test": "failure"},
        {"alert": "failure"},
    )
    assert eff3["alert"] == "success"


def test_gate_verdict_names_blockers():
    mergeable, blockers = gate_verdict({"test": "success", "deploy": "skipped"}, ["test", "deploy"])
    assert mergeable is False and blockers == ["deploy"]
    mergeable, blockers = gate_verdict({"test": "success"}, ["test"])
    assert mergeable is True and blockers == []


# --- Problem 5: end-to-end pipeline ------------------------------------------

def test_full_run_matrix_cache_and_gate():
    wf = _workflow(
        test=_job(
            {"name": "Check out", "uses": "actions/checkout@v4"},
            {"name": "Run tests", "run": "pytest -q"},
            matrix={"axes": {"python": ["3.11", "3.12"]}},
        ),
        deploy=_job(
            {"name": "Deploy", "run": "deploy.sh"},
            needs=["test"],
        ),
    )
    cache = Cache()
    first = run_pipeline(wf, lockfile_text="pandas==2.0.3\n", cache=cache)
    assert first.mergeable is True
    assert first.job_statuses == {
        "test (python=3.11)": "success",
        "test (python=3.12)": "success",
        "deploy": "success",
    }
    # The two test instances miss (new keys); deploy shares the 3.12
    # test instance's OS + Python + lockfile key, so it hits — a cache
    # key stands for its inputs, not for the job that stored it.
    assert first.cache_hits["test (python=3.11)"] is False
    assert first.cache_hits["test (python=3.12)"] is False
    assert first.cache_hits["deploy"] is True
    second = run_pipeline(wf, lockfile_text="pandas==2.0.3\n", cache=cache)
    assert all(hit is True for hit in second.cache_hits.values())
    assert second.mergeable is True


def test_failed_job_blocks_and_dependents_skip_but_always_runs():
    wf = _workflow(
        test=_job({"name": "Run tests", "run": "pytest -q"}),
        deploy=_job({"name": "Deploy", "run": "deploy.sh"}, needs=["test"]),
        notify=_job({"name": "Notify", "run": "notify.sh"}, needs=["deploy"], **{"if": "always"}),
    )
    report = run_pipeline(wf, step_outcomes={"Run tests": False})
    assert report.job_statuses["test"] == "failure"
    assert report.job_statuses["deploy"] == "skipped"
    assert report.job_statuses["notify"] == "success"
    assert report.mergeable is False
    assert "test" in report.blockers and "deploy" in report.blockers


def test_secrets_masked_in_logs_and_artifacts_only_on_success():
    wf = _workflow(
        test=_job(
            {"name": "Leaky step", "run": "echo connecting with s3cret-123"},
            artifacts={"Leaky step": "test-report"},
        ),
    )
    # The artifacts mapping lives on the job dict, not the step: the
    # run reads it from the job, so attach it at job level here.
    wf["jobs"]["test"]["artifacts"] = {"Leaky step": "test-report"}
    report = run_pipeline(wf, secrets={"DB_PASSWORD": "s3cret-123"})
    assert not any("s3cret-123" in line for line in report.logs)
    assert any("***" in line for line in report.logs)
    assert report.artifacts == ["test-report"]
    failed = run_pipeline(
        wf, step_outcomes={"Leaky step": False}, secrets={"DB_PASSWORD": "s3cret-123"}
    )
    assert failed.artifacts == []


def test_invalid_workflow_fails_before_any_job_runs():
    bad = _workflow(test={"runs-on": "ubuntu-latest", "steps": []})
    with pytest.raises(WorkflowError):
        run_pipeline(bad)
