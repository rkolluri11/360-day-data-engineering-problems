"""Problem 2 — typed settings, not loose dict lookups
======================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A dict lookup is a silent ``None`` waiting to happen:
``config["batch_sise"]`` raises, but ``config.get("batch_sise")``
returns ``None`` and the pipeline limps on with a batch size of
nothing. Typed settings turn config into a validated object at
startup — a missing variable fails loudly before the first row
loads, not at 2 AM as a silent ``None``.

This is the stdlib stand-in for pydantic-settings (the post's
example uses it; the repo stays dependency-free, so the same
contract is enforced here with plain Python): ``Settings`` validates
every field at construction, rejects unknown fields so a typo like
``batch_sise`` cannot slip past, and freezes itself so no step can
silently mutate the config mid-run.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Validation is at the DOOR, not at first use: ``batch_size``
    must be a positive int, ``timeout_seconds`` a positive number,
    ``db_host`` a non-empty string, ``environment`` one of
    dev/staging/prod. A bad value raises ``ConfigError`` from the
    constructor, never from deep inside a run.
  - Unknown keyword arguments raise: an unrecognised key is almost
    always a typo, and a typo'd key plus a silently applied default
    is exactly how prod runs against the dev table.
  - Frozen after construction: ``Settings`` uses ``__slots__`` plus
    a locked flag, so assigning to any attribute after construction
    raises ``AttributeError``. One config object, passed around —
    never scattered ``os.getenv`` calls, never mutated in place.
  - ``from_env`` is the single bridge from Problem 1's loader to
    this typed object: it maps the env keys onto field names, so
    the pipeline has exactly one place where strings become types.

Plain words: a typed Settings object is a bouncer at the door.
The wrong name, the wrong type, the wrong range — all turned away
before the party starts, not discovered on the dance floor.
"""

from problem_01_env_not_code import ConfigError, load_config

_ENVIRONMENTS = ("dev", "staging", "prod")
_FIELDS = ("db_host", "batch_size", "timeout_seconds", "environment", "api_key")


class Settings:
    """Validated, frozen pipeline settings. Fails at construction."""

    __slots__ = ("db_host", "batch_size", "timeout_seconds", "environment", "api_key", "_locked")

    def __init__(self, db_host, batch_size=1000, timeout_seconds=30.0,
                 environment="dev", api_key=None):
        if not isinstance(db_host, str) or not db_host.strip():
            raise ConfigError("db_host must be a non-empty string")
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
            raise ConfigError(f"batch_size must be a positive int, got {batch_size!r}")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) \
                or timeout_seconds <= 0:
            raise ConfigError(f"timeout_seconds must be positive, got {timeout_seconds!r}")
        if environment not in _ENVIRONMENTS:
            raise ConfigError(f"environment must be one of {_ENVIRONMENTS}, got {environment!r}")
        if api_key is not None and (not isinstance(api_key, str) or not api_key):
            raise ConfigError("api_key must be a non-empty string when given")
        object.__setattr__(self, "db_host", db_host.strip())
        object.__setattr__(self, "batch_size", batch_size)
        object.__setattr__(self, "timeout_seconds", float(timeout_seconds))
        object.__setattr__(self, "environment", environment)
        object.__setattr__(self, "api_key", api_key)
        object.__setattr__(self, "_locked", True)

    def __setattr__(self, name, value):
        if getattr(self, "_locked", False):
            raise AttributeError("Settings is frozen after construction")
        object.__setattr__(self, name, value)

    def __repr__(self):
        # Never print a secret, even in a debug repr (see Problem 4).
        key = "***" if self.api_key else None
        return (f"Settings(db_host={self.db_host!r}, batch_size={self.batch_size!r}, "
                f"timeout_seconds={self.timeout_seconds!r}, "
                f"environment={self.environment!r}, api_key={key!r})")

    @classmethod
    def from_env(cls, env=None):
        """Build Settings from an env mapping via Problem 1's loader."""
        raw = load_config(env)
        return cls(db_host=raw["DB_HOST"], batch_size=raw["BATCH_SIZE"],
                   api_key=raw["API_KEY"])
