"""Problem 1 — The step that broke when the signature grew
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline step looks like this:

    def clean(rows, batch_size):
        ...

Every caller does ``clean(rows, 10_000)``. One day someone adds a
``retries`` parameter *in the middle*:

    def clean(rows, retries, batch_size):

Every existing caller silently passes 10_000 as ``retries`` and the
default as ``batch_size``. Nothing raises. The pipeline just starts
retrying 10,000 times per failure.

Plain words: positional arguments are a handshake where order is the
only meaning. Add one new hand in the middle and everyone is shaking
the wrong hand.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Your pipeline has 40 steps, each a function taking ``(rows, **config)``
with its own config knobs: ``batch_size``, ``retries``, ``timeout``,
``on_error``... A central ``config.yaml`` holds *every* knob for the
whole pipeline, and a dispatcher calls each step with the full config.

Two things go wrong at 2 AM:
1. A new knob ``deadline`` is added to the YAML for step 12 — and
   steps 1-11 crash with "unexpected keyword argument".
2. A typo'd knob ``batsh_size`` is silently ignored by every step,
   and the pipeline runs unbatched for a week before anyone notices.

Your solution: ``run_step(step_fn, rows, config)`` — a dispatcher
that inspects each step's signature and:
  - passes ONLY the config keys the step declares (extra keys are
    ignored, so new YAML knobs for other steps never break this one),
  - raises a clear error when a required keyword-only knob is missing
    (fail fast, at the call site — not three stages later),
  - steps declaring ``**config`` receive the whole config untouched.

Plain words: each step gets a labeled order slip with only its own
lines on it. The kitchen never sees the bar's drinks, and if the
slip is missing a required line, the waiter is told immediately —
not after the food is cold.

ANALOGY
-------
Ordering at a counter by shouting items in order: add "extra napkins"
in the middle and the cook hears it as the side dish. Ordering on a
labeled ticket: new lines never shift the old ones, and a misspelled
item gets questioned before cooking starts.
"""

from __future__ import annotations

import inspect

_KEYWORD_KINDS = (
    inspect.Parameter.KEYWORD_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
)


def _declared_knobs(step_fn):
    """Config knobs a step accepts by name (excluding the rows arg)."""
    knobs = set()
    for name, param in inspect.signature(step_fn).parameters.items():
        if name == "rows":
            continue
        if param.kind in _KEYWORD_KINDS:
            knobs.add(name)
    return knobs


def _accepts_config_catchall(step_fn):
    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in inspect.signature(step_fn).parameters.values()
    )


def run_step(step_fn, rows, config):
    """Call a pipeline step with only the config knobs it declares.

    - Steps with ``**config`` get the whole config dict.
    - Other steps get exactly the knobs they declare; extra YAML
      knobs meant for other steps are ignored, so growing the
      config never breaks old steps.
    - Missing *required* knobs raise TypeError naming the step and
      the missing knobs (fail fast, at the call site).
    """
    if _accepts_config_catchall(step_fn):
        return step_fn(rows, **dict(config))

    knobs = _declared_knobs(step_fn)
    kwargs = {k: v for k, v in config.items() if k in knobs}

    missing = [
        name
        for name, param in inspect.signature(step_fn).parameters.items()
        if name != "rows"
        and param.kind in _KEYWORD_KINDS
        and param.default is inspect.Parameter.empty
        and name not in kwargs
    ]
    if missing:
        raise TypeError(
            f"{step_fn.__name__}() missing required config knob(s): "
            f"{', '.join(missing)}"
        )
    return step_fn(rows, **kwargs)


# --- Example steps -------------------------------------------------------

def clean(rows, *, batch_size, retries=3):
    """Drop empty rows in batches; retry transient failures."""
    out = [r for r in rows if r]
    return {"cleaned": out, "batches": -(-len(out) // batch_size),
            "retries_allowed": retries}


def enrich(rows, *, timeout, on_error="skip", **config):
    """Catch-all step: sees every knob, picks what it needs."""
    return {"rows": rows, "timeout": timeout, "on_error": on_error,
            "extra_knobs_seen": sorted(set(config) - {"timeout", "on_error"})}


if __name__ == "__main__":
    rows = [{"id": 1}, {}, {"id": 2}]
    config = {"batch_size": 2, "timeout": 30, "deadline": "2026-10-05"}
    print(run_step(clean, rows, config))    # 'deadline' ignored, no crash
    print(run_step(enrich, rows, config))  # catch-all sees everything
