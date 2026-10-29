"""Problem 1 — a workflow is a contract: validate it before CI runs it.

THE PROBLEM (beginner foothold first)
------------------------------------
A GitHub Actions workflow is a YAML file that says: on this trigger,
run these jobs, each job runs these steps. If the file is wrong — a
job with no steps, a step with neither a command nor an action, a job
that needs a job that does not exist — CI does not fail politely at
the top. It fails halfway through, or never starts, and the pipeline
author gets a cryptic error instead of a clear one.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A workflow needs a name, at least one trigger, and at least one job.
  - A trigger is one of push, pull_request, schedule, or
    workflow_dispatch. A schedule trigger carries cron expressions,
    and a cron expression has exactly five fields in valid ranges —
    a six-field cron or a minute of 61 is a config bug, not a
    schedule.
  - A job needs an id, a runs-on runner, and at least one step.
    A job's needs must name jobs that actually exist in the same
    workflow, and a job may not need itself.
  - A step needs a name and exactly one of run (a shell command) or
    uses (an action). Both is ambiguous; neither is nothing to do.
    A uses value must name an action version: "actions/checkout@v4",
    not a bare "actions/checkout".
  - Validation fails loudly at parse time, naming the broken part —
    a bad workflow that is silently accepted is worse than no CI.

Plain words: validate the recipe before you start cooking — a missing
ingredient found at the stove is a wasted evening; found in the
recipe, it is a one-line fix.
"""

import re

ALLOWED_TRIGGERS = ("push", "pull_request", "schedule", "workflow_dispatch")
_JOB_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# minute, hour, day-of-month, month, day-of-week
_CRON_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


class WorkflowError(ValueError):
    """Raised for a malformed workflow, job, step, trigger, or cron."""


def validate_cron(expression):
    """Return True if ``expression`` is a valid five-field cron string.

    Each field may be ``*``, ``*/n``, a single number, a ``a-b`` range,
    or a comma list of those. Numbers must fall in the field's range.
    Anything else — wrong field count, a 61st minute, a bare step —
    returns False instead of raising, so callers can collect errors.
    """
    if not isinstance(expression, str):
        return False
    fields = expression.split()
    if len(fields) != 5:
        return False
    for field, (low, high) in zip(fields, _CRON_RANGES):
        for part in field.split(","):
            if part == "*":
                continue
            if part.startswith("*/"):
                step = part[2:]
                if not step.isdigit() or int(step) < 1:
                    return False
                continue
            if "-" in part:
                start, _, end = part.partition("-")
                if not (start.isdigit() and end.isdigit()):
                    return False
                if not (low <= int(start) <= high and low <= int(end) <= high):
                    return False
                if int(start) > int(end):
                    return False
                continue
            if not part.isdigit() or not (low <= int(part) <= high):
                return False
    return True


def validate_env_name(name):
    """Return True if ``name`` is a legal environment-variable name."""
    return isinstance(name, str) and bool(_ENV_NAME_RE.match(name))


class Step:
    """One step of a job: a name plus exactly one of run / uses."""

    def __init__(self, name, run=None, uses=None, env=None):
        self.name = name
        self.run = run
        self.uses = uses
        self.env = dict(env or {})

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise WorkflowError("step needs a non-empty name")
        if bool(self.run) == bool(self.uses):
            raise WorkflowError(
                f"step {self.name!r} needs exactly one of run / uses"
            )
        if self.uses is not None:
            if "@" not in self.uses or self.uses.split("@", 1)[1].strip() == "":
                raise WorkflowError(
                    f"step {self.name!r} uses {self.uses!r}: "
                    "an action must pin a version, e.g. actions/checkout@v4"
                )
        for key in self.env:
            if not validate_env_name(key):
                raise WorkflowError(f"step {self.name!r}: bad env name {key!r}")
        return self

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise WorkflowError(f"step must be a mapping, got {data!r}")
        return cls(
            name=data.get("name"),
            run=data.get("run"),
            uses=data.get("uses"),
            env=data.get("env") or {},
        ).validate()


class Job:
    """One job: an id, a runner, steps, and optional needs / env."""

    def __init__(self, job_id, runs_on, steps, needs=None, env=None):
        self.job_id = job_id
        self.runs_on = runs_on
        self.steps = list(steps)
        self.needs = list(needs or [])
        self.env = dict(env or {})

    def validate(self, known_job_ids=None):
        if not isinstance(self.job_id, str) or not _JOB_ID_RE.match(self.job_id):
            raise WorkflowError(f"bad job id {self.job_id!r}")
        if not isinstance(self.runs_on, str) or not self.runs_on.strip():
            raise WorkflowError(f"job {self.job_id!r} needs a runs-on runner")
        if not self.steps:
            raise WorkflowError(f"job {self.job_id!r} needs at least one step")
        for step in self.steps:
            step.validate()
        if self.job_id in self.needs:
            raise WorkflowError(f"job {self.job_id!r} may not need itself")
        if known_job_ids is not None:
            for needed in self.needs:
                if needed not in known_job_ids:
                    raise WorkflowError(
                        f"job {self.job_id!r} needs unknown job {needed!r}"
                    )
        for key in self.env:
            if not validate_env_name(key):
                raise WorkflowError(f"job {self.job_id!r}: bad env name {key!r}")
        return self

    @classmethod
    def from_dict(cls, job_id, data):
        if not isinstance(data, dict):
            raise WorkflowError(f"job {job_id!r} must be a mapping")
        return cls(
            job_id=job_id,
            runs_on=data.get("runs-on"),
            steps=[Step.from_dict(s) for s in data.get("steps", [])],
            needs=data.get("needs") or [],
            env=data.get("env") or {},
        )


class Workflow:
    """A whole workflow: name, triggers, and jobs, validated together."""

    def __init__(self, name, triggers, jobs, schedules=None):
        self.name = name
        self.triggers = list(triggers)
        self.jobs = list(jobs)
        self.schedules = list(schedules or [])

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise WorkflowError("workflow needs a non-empty name")
        if not self.triggers:
            raise WorkflowError("workflow needs at least one trigger")
        for trigger in self.triggers:
            if trigger not in ALLOWED_TRIGGERS:
                raise WorkflowError(f"unknown trigger {trigger!r}")
        if "schedule" in self.triggers:
            if not self.schedules:
                raise WorkflowError("schedule trigger needs at least one cron")
            for cron in self.schedules:
                if not validate_cron(cron):
                    raise WorkflowError(f"invalid cron expression {cron!r}")
        if not self.jobs:
            raise WorkflowError("workflow needs at least one job")
        ids = [job.job_id for job in self.jobs]
        if len(set(ids)) != len(ids):
            raise WorkflowError(f"duplicate job ids in {ids!r}")
        known = set(ids)
        for job in self.jobs:
            job.validate(known_job_ids=known)
        return self

    @classmethod
    def from_dict(cls, data):
        """Build and validate a Workflow from a plain-dict structure.

        ``data`` uses the GitHub Actions shapes: ``name``, ``on`` (a
        string, a list, or a mapping whose keys are trigger names and
        whose ``schedule`` value is a list of ``{"cron": ...}``
        mappings), and ``jobs`` (a mapping of job id to job dict).
        """
        if not isinstance(data, dict):
            raise WorkflowError(f"workflow must be a mapping, got {data!r}")
        on = data.get("on")
        schedules = []
        if isinstance(on, str):
            triggers = [on]
        elif isinstance(on, list):
            triggers = list(on)
        elif isinstance(on, dict):
            triggers = list(on.keys())
            for entry in on.get("schedule") or []:
                if isinstance(entry, dict) and "cron" in entry:
                    schedules.append(entry["cron"])
                elif isinstance(entry, str):
                    schedules.append(entry)
        else:
            triggers = []
        jobs = [
            Job.from_dict(job_id, job_data)
            for job_id, job_data in (data.get("jobs") or {}).items()
        ]
        return cls(
            name=data.get("name"),
            triggers=triggers,
            jobs=jobs,
            schedules=schedules,
        ).validate()

    def summary(self):
        """Small counts dict — handy for a CI log line."""
        return {
            "name": self.name,
            "triggers": list(self.triggers),
            "jobs": len(self.jobs),
            "steps": sum(len(job.steps) for job in self.jobs),
        }


if __name__ == "__main__":
    wf = Workflow.from_dict(
        {
            "name": "pipeline-ci",
            "on": {"push": {}, "schedule": [{"cron": "0 2 * * *"}]},
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"name": "Check out", "uses": "actions/checkout@v4"},
                        {"name": "Run tests", "run": "pytest -q"},
                    ],
                },
            },
        }
    )
    print(wf.summary())
