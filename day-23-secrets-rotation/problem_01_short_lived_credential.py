"""Problem 1 — short-lived credentials: a key that expires on its own
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A hotel key card stops working at checkout, even though nobody told
the door anything. That is the whole idea: instead of one master key
that works forever (and is a disaster the day it leaks), a pipeline
credential is born with an expiry date. If it leaks, the damage has
a deadline. If it is forgotten in a log file, it is useless by the
time anyone finds it.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Expiry is computed, never guessed: ``expires_at`` is
    ``issued_at + ttl_seconds``. A credential with no expiry is
    rejected at construction — "forever" is not a default.
  - Time is injected, never read off the wall clock inside the
    check: ``is_expired(now)`` takes ``now`` so tests are
    deterministic and a pipeline can ask "was this valid when the
    row was written?" instead of only "is it valid right now?"
  - Naive datetimes are rejected: mixing a naive ``issued_at``
    with an aware ``now`` fails silently in some code and loudly
    in others, so this module fails loudly, at construction.
  - The secret never appears in ``repr``: a credential printed
    into a log shows ``***``, the id, and the expiry — never the
    value itself. (Day 22 covered masking; rotation builds on it.)

Plain words: a credential is a hotel key card, not a house key.
It should stop working by itself, on a date everyone can see.
"""

from datetime import datetime, timedelta, timezone


class CredentialError(ValueError):
    """Raised for an unusable credential: bad construction or expiry."""


def _require_aware(moment, name):
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise CredentialError(f"{name} must be timezone-aware, got naive datetime")
    return moment


def utcnow():
    """Current time, timezone-aware. Only a convenience, never a default inside checks."""
    return datetime.now(timezone.utc)


class Credential:
    """One short-lived credential: an id, a secret value, and a deadline."""

    def __init__(self, credential_id, secret, issued_at, ttl_seconds):
        if not credential_id or not str(credential_id).strip():
            raise CredentialError("credential_id must be non-empty")
        if not secret:
            raise CredentialError("secret must be non-empty")
        if ttl_seconds <= 0:
            raise CredentialError(f"ttl_seconds must be positive, got {ttl_seconds!r}")
        self.credential_id = credential_id
        self.secret = secret
        self.issued_at = _require_aware(issued_at, "issued_at")
        self.ttl_seconds = ttl_seconds

    @property
    def expires_at(self):
        return self.issued_at + timedelta(seconds=self.ttl_seconds)

    def seconds_remaining(self, now=None):
        """Seconds left at ``now`` (negative once expired)."""
        now = _require_aware(now if now is not None else utcnow(), "now")
        return (self.expires_at - now).total_seconds()

    def is_expired(self, now=None):
        return self.seconds_remaining(now) <= 0

    def is_valid(self, now=None):
        return not self.is_expired(now)

    def __repr__(self):
        return (f"Credential(id={self.credential_id!r}, secret='***', "
                f"expires_at={self.expires_at.isoformat()})")
