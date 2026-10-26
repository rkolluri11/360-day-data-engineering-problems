"""Problem 1 — env vars, not code: the values that change live outside the code
================================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline worked on a laptop and died in prod. Nothing changed in
the code — only the config it silently carried with it. A batch job
ran fine in staging, then its first prod run wrote a day of events
to the DEV table. Nothing errored — the pipeline was "green" — and
Monday's dashboard was empty until someone noticed the host was
hardcoded in a helper nobody had touched in months.

The twelve-factor rule, plain version: if a value changes between
machines, it comes from the environment, not from a line you edited
by hand. The database host, the batch size, the API key — those are
not code. They live outside it, so the same code runs in dev,
staging, and prod.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A missing variable must fail LOUDLY at startup, before the
    first row loads — not at 2 AM as a silent ``None`` that writes
    to the wrong table. ``load_config`` raises ``ConfigError`` for
    every missing required key, naming the key.
  - Env vars are strings; the pipeline needs ints and bools.
    Coercion happens once, here, with a clear error when
    ``BATCH_SIZE="lots"`` cannot become an int — never a
    half-coerced value leaking downstream.
  - No scattered ``os.getenv`` calls: one loader, one place to
    change. The caller passes an explicit env mapping (defaulting
    to ``os.environ``) so tests never mutate the real environment.
  - Unknown keys are ignored, not rejected: a loader that crashes
    on an unrelated ``PATH`` entry is worse than useless. (Strict
    typo-catching lives in Problem 2's typed Settings.)

Plain words: config is the dials on the machine, not the machine
itself. You should be able to turn a dial without rebuilding the
machine — and without opening it up to see which dial is which.
"""

import os


class ConfigError(ValueError):
    """Raised when config is missing or cannot be coerced, at load time."""


# (key, kind, default) — default of None means REQUIRED.
SPEC = [
    ("DB_HOST", str, None),
    ("BATCH_SIZE", int, 1000),
    ("DRY_RUN", bool, False),
    ("API_KEY", str, None),
]


def _coerce(key, raw, kind):
    if kind is str:
        return raw
    if kind is int:
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"{key} must be an integer, got {raw!r}") from None
    if kind is bool:
        lowered = raw.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off", ""):
            return False
        raise ConfigError(f"{key} must be a boolean, got {raw!r}")
    raise ConfigError(f"unknown kind {kind!r} for {key}")


def load_config(env=None):
    """Load the pipeline's config from an env mapping.

    Returns a plain dict. Raises ConfigError naming any missing
    required key or any value that cannot be coerced.
    """
    env = os.environ if env is None else env
    config = {}
    for key, kind, default in SPEC:
        raw = env.get(key)
        if raw is None:
            if default is None:
                raise ConfigError(f"missing required config: {key}")
            config[key] = default
        else:
            config[key] = _coerce(key, raw, kind)
    return config
