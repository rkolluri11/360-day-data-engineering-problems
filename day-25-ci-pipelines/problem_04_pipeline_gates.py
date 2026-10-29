"""Problem 4 — the gate decides: does this run get to merge?

THE PROBLEM (beginner foothold first)
------------------------------------
A pull request is not "tests passed" — it is "every required check
passed". If lint passed but the test job never ran because its
dependency failed, merging on "one green check" ships untested code.
The gate is the rule that turns a pile of job results into one
merge decision.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Jobs form a dependency graph (job -> jobs it needs). The run
    order is topological: a job runs only after its needs, in a
    deterministic order. A cycle is an error, not an infinite loop,
    and a need naming an unknown job is an error, not a silent skip.
  - A job's effective status follows its condition: the default
    ("success") runs only if every need succeeded; "always" runs
    whatever its needs did (the cleanup / notify job); "failure"
    runs only if at least one need failed. A job whose condition is
    not met is "skipped", whatever its own step outcome would be.
  - The gate verdict is strict: mergeable only if every required
    job is present and effectively "success". Anything else —
    missing, failed, skipped, cancelled — blocks, and the verdict
    names the blockers so a human can see exactly what to fix.

Plain words: the gate is the bouncer with a list — every name on the
required list must be inside and green, or nobody gets in, and the
bouncer says exactly who is missing.
"""

from collections import deque


class GateError(ValueError):
    """Raised for a cyclic or dangling job-dependency graph."""


STATUSES = ("success", "failure", "cancelled", "skipped")
CONDITIONS = ("success", "always", "failure")


def order_jobs(needs_map):
    """Return job ids in topological order (needs before dependents).

    Ready jobs are emitted in the order they first appear in
    ``needs_map``, so the order is deterministic. A cycle raises
    GateError; a need naming an unknown job raises GateError.
    """
    needs = {job: list(needs or []) for job, needs in needs_map.items()}
    for job, deps in needs.items():
        for dep in deps:
            if dep not in needs:
                raise GateError(f"job {job!r} needs unknown job {dep!r}")
            if dep == job:
                raise GateError(f"job {job!r} needs itself")
    indegree = {job: 0 for job in needs}
    dependents = {job: [] for job in needs}
    for job, deps in needs.items():
        for dep in deps:
            dependents[dep].append(job)
            indegree[job] += 1
    ready = deque(job for job in needs if indegree[job] == 0)
    order = []
    while ready:
        job = ready.popleft()
        order.append(job)
        for dependent in dependents[job]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if len(order) != len(needs):
        raise GateError(f"dependency cycle among {sorted(needs)!r}")
    return order


def effective_statuses(needs_map, own_status, conditions=None):
    """Compute each job's effective status after dependency gating.

    ``own_status`` is what a job's steps would report if it ran
    (default "success" for jobs not listed). ``conditions`` maps a
    job to "success" (default), "always", or "failure". A job whose
    condition is not met reports "skipped" and its steps never run.
    """
    conditions = conditions or {}
    for job, status in own_status.items():
        if status not in STATUSES:
            raise GateError(f"job {job!r} has unknown status {status!r}")
    for job, condition in conditions.items():
        if condition not in CONDITIONS:
            raise GateError(f"job {job!r} has unknown condition {condition!r}")
    effective = {}
    for job in order_jobs(needs_map):
        condition = conditions.get(job, "success")
        dep_statuses = [effective[dep] for dep in (needs_map.get(job) or [])]
        if condition == "success" and any(s != "success" for s in dep_statuses):
            effective[job] = "skipped"
        elif condition == "failure" and not any(s == "failure" for s in dep_statuses):
            effective[job] = "skipped"
        else:
            effective[job] = own_status.get(job, "success")
    return effective


def gate_verdict(effective, required):
    """Return (mergeable, blockers) for ``required`` job ids.

    Mergeable only if every required job is present and "success".
    Blockers list every required job that is missing or not success,
    in the order given — the exact list a reviewer needs to fix.
    """
    blockers = [
        job for job in required if effective.get(job) != "success"
    ]
    return (not blockers, blockers)


if __name__ == "__main__":
    needs = {"test": [], "deploy": ["test"], "notify": ["deploy"]}
    eff = effective_statuses(
        needs, {"test": "success", "deploy": "failure"}, {"notify": "always"}
    )
    print(eff)
    print(gate_verdict(eff, ["test", "deploy"]))
