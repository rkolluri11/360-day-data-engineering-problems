"""Problem 5 — the CI pipeline end to end: validate, expand, run, gate.

THE PROBLEM (beginner foothold first)
------------------------------------
Problems 1–4 are the parts; a pipeline run is the whole. Given a
workflow, a matrix, a cache, and a secret store, a run must: reject
a bad workflow before anything runs, fan one job out into its matrix
combinations, reuse the cache when the lockfile matches, run each
job's steps in dependency order, mask every secret out of the logs,
and end with one gate verdict — mergeable or blocked, with names.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Validation comes first: an invalid workflow produces no job
    results and no logs — the run fails before the first step.
  - Matrix jobs fan out to one instance per combination, named
    "job (axis=value, ...)". A job with no matrix runs once.
  - Steps run only when their job's gate condition allows it (see
    Problem 4); a skipped job contributes no step logs and no
    artifacts. A failed step fails its job, and dependents of a
    failed job are skipped unless they asked for "always".
  - Cache keys are built per job instance from its matrix Python
    version (default "3.12"), the OS in runs-on, and the lockfile
    text; a hit is recorded, never assumed — the first run misses,
    the second hits.
  - Logs are masked with the secret store before they are returned,
    so a step that echoes a secret leaves only "***" behind.
  - Artifacts come only from successful jobs: a step may declare an
    "artifact" name, collected only if its job ends "success".
  - The report is one object: per-instance statuses, cache hits,
    masked logs, artifacts, and the gate verdict for the required
    jobs (required = every job instance, unless the caller says
    otherwise).

Plain words: the run is the dress rehearsal with the audience
already in — validate the script, run every scene in order, hide
the passwords from the programme, and only then ask the bouncer
whether the show merges.
"""

from problem_01_workflow_model import Workflow
from problem_02_matrix_and_cache import (
    apply_include_exclude,
    cache_key,
    expand_matrix,
)
from problem_03_secrets_and_env import SecretStore
from problem_04_pipeline_gates import (
    effective_statuses,
    gate_verdict,
    order_jobs,
)


class RunReport:
    """The outcome of one simulated CI run."""

    def __init__(self, job_statuses, cache_hits, logs, artifacts, mergeable, blockers):
        self.job_statuses = job_statuses
        self.cache_hits = cache_hits
        self.logs = logs
        self.artifacts = artifacts
        self.mergeable = mergeable
        self.blockers = blockers

    def __repr__(self):
        return (
            f"RunReport(mergeable={self.mergeable}, "
            f"jobs={self.job_statuses!r}, blockers={self.blockers!r})"
        )


def _instance_name(job_id, combo):
    if not combo:
        return job_id
    inner = ", ".join(f"{k}={v}" for k, v in combo.items())
    return f"{job_id} ({inner})"


def run_pipeline(workflow_data, step_outcomes=None, lockfile_text="",
                 secrets=None, cache=None, required=None):
    """Simulate one CI run; return a RunReport.

    ``step_outcomes`` maps a step name to True (pass) or False (fail);
    steps not listed pass. ``cache`` is a Problem 2 Cache (a fresh
    one is created when omitted, so a single run never self-hits).
    ``required`` lists the job instances the gate checks; by default
    every job instance is required.
    """
    from problem_02_matrix_and_cache import Cache

    workflow = Workflow.from_dict(workflow_data)
    store = secrets if isinstance(secrets, SecretStore) else SecretStore(secrets)
    cache = cache if cache is not None else Cache()
    outcomes = step_outcomes or {}

    # Fan jobs out over their matrices. A dependent instance needs
    # every instance of each job it depends on.
    instances = {}  # instance name -> (job, combo)
    for job in workflow.jobs:
        job_data = (workflow_data.get("jobs") or {}).get(job.job_id, {})
        matrix = job_data.get("matrix")
        combos = [{}]
        if matrix:
            combos = expand_matrix(matrix.get("axes") or {})
            combos = apply_include_exclude(
                combos,
                include=matrix.get("include"),
                exclude=matrix.get("exclude"),
            )
        for combo in combos:
            instances[_instance_name(job.job_id, combo)] = (job, combo)
    needs_map = {}
    for name, (job, _combo) in instances.items():
        expanded = []
        for dep in job.needs:
            expanded.extend(
                inst for inst, (dep_job, _c) in instances.items()
                if dep_job.job_id == dep
            )
        needs_map[name] = expanded

    order = order_jobs(needs_map)

    # Step outcomes per instance, in dependency order.
    own_status = {}
    logs = []
    artifacts = []
    cache_hits = {}
    conditions = {}
    for name in order:
        job, combo = instances[name]
        job_data = (workflow_data.get("jobs") or {}).get(job.job_id, {})
        conditions[name] = job_data.get("if", "success")
        # Step outcomes are recorded for every job first; the gate in
        # effective_statuses then decides which jobs actually ran.
        failed = False
        for step in job.steps:
            passed = outcomes.get(step.name, True)
            if not passed:
                failed = True
        own_status[name] = "failure" if failed else "success"
    effective = effective_statuses(needs_map, own_status, conditions)

    # Second pass: cache, logs, and artifacts only for jobs that ran.
    for name in order:
        job, combo = instances[name]
        if effective[name] == "skipped":
            logs.append(f"{name}: skipped")
            continue
        python_version = str(combo.get("python", "3.12"))
        key = cache_key(job.runs_on, python_version, lockfile_text)
        cache_hits[name] = cache.hit_or_store(key)
        for step in job.steps:
            passed = outcomes.get(step.name, True)
            logs.append(f"{name}: step {step.name!r} {'passed' if passed else 'failed'}")
            if step.run:
                logs.append(f"{name}: $ {step.run}")
        if effective[name] == "success":
            job_data = (workflow_data.get("jobs") or {}).get(job.job_id, {})
            for step in job.steps:
                artifact = (job_data.get("artifacts") or {}).get(step.name)
                if artifact:
                    artifacts.append(artifact)
    masked_logs = [store.mask(line) for line in logs]
    required_instances = required if required is not None else list(instances)
    mergeable, blockers = gate_verdict(effective, required_instances)
    return RunReport(
        job_statuses=effective,
        cache_hits=cache_hits,
        logs=masked_logs,
        artifacts=artifacts,
        mergeable=mergeable,
        blockers=blockers,
    )

if __name__ == "__main__":
    report = run_pipeline(
        {
            "name": "pipeline-ci",
            "on": ["push"],
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "matrix": {"axes": {"python": ["3.11", "3.12"]}},
                    "steps": [
                        {"name": "Check out", "uses": "actions/checkout@v4"},
                        {"name": "Run tests", "run": "pytest -q"},
                    ],
                },
            },
        },
        lockfile_text="pandas==2.0.3\n",
    )
    print(report)
    print(report.logs)
