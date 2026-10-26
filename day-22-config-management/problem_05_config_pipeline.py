"""Problem 5 — the pipeline end to end: one code path, every environment
=========================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
The whole day in one pipeline: the same code runs in dev and in
prod, and the ONLY thing that changes is the config it is handed.
``build_pipeline_config`` takes defaults, a YAML text, an env
mapping, and a secrets mapping, resolves them with Problem 3's
precedence, validates the result into Problem 2's typed Settings,
and returns a pipeline object that carries no config-loading logic
of its own. A bad config fails at build time — before any row is
processed, before any table is touched.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Fail-fast is a TESTED property, not a hope: ``run`` refuses
    to process rows if the config was never built, and a config
    that fails validation never produces a pipeline at all. The
    test that proves this runs the bad config first and asserts
    zero rows were touched.
  - Dev and prod are the same code path: ``run`` sums the same
    way in both; only ``db_host``/``batch_size``/``environment``
    differ, because they came from different configs. The test
    runs both and asserts identical results with different
    destinations — the proof that config, not code, changed.
  - Batching honours the config: rows are consumed in chunks of
    ``batch_size``, and the pipeline records how many batches ran
    — a batch size of 2 over 5 rows is 3 batches, not 1, not 5.
  - The pipeline never logs secrets: its ``describe`` output is
    built from ``mask_config`` (Problem 4), so even a debug dump
    of a running pipeline cannot leak the key.

Plain words: the pipeline is a train, the config is the track
layout. The same train runs the dev loop and the prod main line —
you do not rebuild the train to change where it goes, you just
lay different track, and you check the track before the train
moves.
"""

from problem_01_env_not_code import ConfigError
from problem_02_typed_settings import Settings
from problem_03_precedence import resolve
from problem_04_secrets_never_logged import mask_config

DEFAULTS = {
    "database": {"host": "localhost", "port": 5432},
    "batch": {"size": 1000},
    "environment": "dev",
}

_ENV_TO_NESTED = {
    "DATABASE_HOST": ("database", "host"),
    "DATABASE_PORT": ("database", "port"),
    "BATCH_SIZE": ("batch", "size"),
    "ENVIRONMENT": ("environment",),
}


def build_pipeline_config(yaml_text="", env=None, secrets=None):
    """Resolve + validate config. Returns (Settings, masked_render).

    ``env``/``secrets`` use the flat keys of ``_ENV_TO_NESTED`` plus
    ``API_KEY`` for the secret. Raises ConfigError on any bad value.
    """
    env = env or {}
    secrets = secrets or {}
    flat_env = {}
    for key, value in env.items():
        if key in _ENV_TO_NESTED:
            flat_env["_".join(_ENV_TO_NESTED[key]).upper()] = value
    flat_secrets = {}
    for key, value in secrets.items():
        if key in _ENV_TO_NESTED:
            flat_secrets["_".join(_ENV_TO_NESTED[key]).upper()] = value
    merged = resolve(DEFAULTS, yaml_text, flat_env, flat_secrets)
    # API_KEY bypasses resolve's flattening so it stays one key named
    # "api_key" — the name mask_config (Problem 4) recognises as secret.
    # Secrets beat env for the key, per the documented precedence.
    api_key = secrets.get("API_KEY", env.get("API_KEY"))
    if api_key is not None:
        merged["api_key"] = api_key
    try:
        settings = Settings(
            db_host=str(merged["database"]["host"]),
            batch_size=int(merged["batch"]["size"]),
            environment=str(merged["environment"]),
            api_key=api_key,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"invalid pipeline config: {exc}") from None
    return settings, mask_config(merged)


class Pipeline:
    """A toy batch pipeline: same code, any config, secrets never logged."""

    def __init__(self, settings):
        if not isinstance(settings, Settings):
            raise ConfigError("Pipeline needs validated Settings, not raw config")
        self.settings = settings
        self.batches_run = 0
        self.rows_seen = 0

    def describe(self):
        """Safe-to-log description: destination + shape, never secrets."""
        return (f"Pipeline -> {self.settings.db_host} "
                f"[{self.settings.environment}] "
                f"batch_size={self.settings.batch_size} "
                f"api_key={'***' if self.settings.api_key else None}")

    def run(self, rows):
        """Sum ``amount`` per row in batches of settings.batch_size."""
        rows = list(rows)
        total = 0.0
        for start in range(0, len(rows), self.settings.batch_size):
            chunk = rows[start:start + self.settings.batch_size]
            total += sum(row["amount"] for row in chunk)
            self.batches_run += 1
        self.rows_seen += len(rows)
        return total
