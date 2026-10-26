"""Problem 4 — secrets: never committed, never logged, never printed
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Which config bug burned you — a secret in the repo, the wrong
environment, or a magic number nobody could explain? The first one
is the most expensive: a secret committed to git is compromised
the moment it is pushed, even if you delete it in the next commit
— history remembers. A secret printed to a log is compromised the
moment the log ships somewhere it should not be.

So three rules, enforced in code, not in a wiki page nobody reads:
a ``.env`` file is gitignored, never committed, never logged; a
secrets mapping overrides env at the top of the precedence stack
(Problem 3) so a rotated secret takes effect without touching any
file; and every rendering of config — repr, log line, error
message — masks secret values.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``parse_dotenv`` reads ``KEY=value`` lines, skips blanks and
    ``#`` comments, strips matching quotes, and ignores
    ``export `` prefixes. A malformed line raises ``ConfigError``
    naming the line — a silently skipped line is a missing secret
    that fails somewhere worse.
  - Masking is by KEY NAME, not by value: ``mask_config`` walks
    nested dicts and replaces the value of any key whose name
    contains ``password``, ``secret``, ``token``, or ``api_key``
    (case-insensitive) with ``"***"``. Masking by value fails the
    moment the same string appears somewhere innocent.
  - ``mask_config`` returns a NEW dict — the original keeps the
    real secret for the code that needs it, and only the rendered
    copy is safe to log.
  - ``Secret`` is a tiny wrapper for values that must never leak
    through an accidental print: its ``repr`` and ``str`` both
    show ``"***"``, and only ``reveal()`` returns the value, so
    the leak requires an explicit, greppable call.

Plain words: a secret is a house key. You do not photocopy it
into the team newsletter, and you do not leave it taped to the
front door — you keep it in one pocket, and you hand it over only
when the lock is right in front of you.
"""

from problem_01_env_not_code import ConfigError

_SECRET_HINTS = ("password", "secret", "token", "api_key")


def parse_dotenv(text):
    """Parse .env text into a dict. Malformed lines raise ConfigError."""
    values = {}
    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            raise ConfigError(f".env line {lineno}: expected KEY=value")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigError(f".env line {lineno}: empty key")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def mask_config(config):
    """Return a copy of ``config`` with secret values replaced by '***'."""
    masked = {}
    for key, value in config.items():
        if isinstance(value, dict):
            masked[key] = mask_config(value)
        elif any(hint in str(key).lower() for hint in _SECRET_HINTS):
            masked[key] = "***"
        else:
            masked[key] = value
    return masked


class Secret:
    """A value that refuses to print itself. Reveal only on purpose."""

    def __init__(self, value):
        if not isinstance(value, str) or not value:
            raise ConfigError("Secret must be a non-empty string")
        self._value = value

    def reveal(self):
        return self._value

    def __repr__(self):
        return "Secret('***')"

    def __str__(self):
        return "***"
