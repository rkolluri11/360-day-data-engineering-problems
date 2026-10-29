"""Problem 3 — secrets must never reach the log, env must resolve in order.

THE PROBLEM (beginner foothold first)
------------------------------------
A CI job needs a database password, but the log is public to everyone
with repo access. If a step prints the password, it is leaked the
moment the log is saved — rotating after the fact does not un-print
it. And three layers of environment — workflow, job, step — must
resolve in one order, or a step silently runs against the wrong
database.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Log masking replaces every secret occurrence with "***". Secrets
    are masked longest-first, so a short secret that is a prefix of
    a longer one cannot leave the longer one's tail visible. Empty
    secrets are ignored — replacing "" would corrupt every string.
  - Env precedence is fixed: step beats job beats workflow. A key
    set at two levels resolves to the most specific value, and keys
    set at only one level survive untouched.
  - Env names are validated: a name that is not a legal variable
    name is a config bug, caught before the job runs.
  - A secret store never reveals its values: its repr, its listing,
    and its log-safe view expose names only. The one way to get a
    value back is an explicit get by name — the code that needs it,
    not the code that prints it.

Plain words: treat a secret like a password spoken in a crowded room
— mask it before it reaches the log, and never print the room's
guest list with the passwords attached.
"""

import re

_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MASK = "***"


class EnvError(ValueError):
    """Raised for an illegal environment-variable name."""


def validate_env_name(name):
    """Return True if ``name`` is a legal environment-variable name."""
    return isinstance(name, str) and bool(_ENV_NAME_RE.match(name))


def mask_text(text, secrets):
    """Return ``text`` with every occurrence of every secret masked.

    Secrets are applied longest-first and empty secrets are skipped,
    so overlapping secrets cannot leak a tail and "" cannot corrupt
    the text. Non-string secrets are ignored.
    """
    masked = text
    clean = [s for s in secrets if isinstance(s, str) and s]
    for secret in sorted(clean, key=len, reverse=True):
        masked = masked.replace(secret, MASK)
    return masked


def resolve_env(workflow_env=None, job_env=None, step_env=None):
    """Merge env layers with precedence step > job > workflow.

    Returns a new dict. Any illegal env name in any layer raises
    EnvError before merging, so a bad name never reaches a runner.
    """
    merged = {}
    for layer in (workflow_env, job_env, step_env):
        for key, value in (layer or {}).items():
            if not validate_env_name(key):
                raise EnvError(f"illegal env name {key!r}")
            merged[key] = value
    return merged


def log_safe_env(env, secret_names):
    """Return a copy of ``env`` with secret-named values masked."""
    secret_set = set(secret_names or [])
    return {
        key: (MASK if key in secret_set else value) for key, value in env.items()
    }


class SecretStore:
    """A name -> secret mapping that never prints its values."""

    def __init__(self, secrets=None):
        self._secrets = dict(secrets or {})

    def get(self, name):
        """Return the secret for ``name``; KeyError if it is not stored."""
        return self._secrets[name]

    def has(self, name):
        return name in self._secrets

    def names(self):
        """Return the stored secret names — never the values."""
        return sorted(self._secrets)

    def mask(self, text):
        """Mask every stored secret in ``text``."""
        return mask_text(text, self._secrets.values())

    def __repr__(self):
        return f"SecretStore(names={self.names()!r})"


if __name__ == "__main__":
    store = SecretStore({"DB_PASSWORD": "s3cret-123"})
    env = resolve_env({"DB": "prod"}, {"DB": "staging"}, {"RETRIES": "3"})
    print(env)
    print(store.mask("connecting with s3cret-123 to prod"))
    print(store)
