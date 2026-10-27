"""Problem 2 — rotate without downtime: change the lock, keep the door open
=============================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You cannot change every lock in a building at the same instant.
While the new keys go out, some doors still see the old key — and
a pipeline that swaps credentials in one hard cut drops every
in-flight request that was already holding the old one. The fix is
an overlap window: for a short grace period, BOTH keys work. Then
the old key stops, on schedule, not by accident.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - One current credential, at most one previous: ``rotate`` moves
    the current credential to ``previous`` and installs the new
    one. Rotating twice in a row does not resurrect a credential
    from two generations ago.
  - Grace is a deadline, not a feeling: the previous credential
    validates only while ``now <= rotated_at + grace_seconds``.
    One second past grace, it is dead — even if it has not
    technically expired yet.
  - Expiry still beats grace: a previous credential that already
    expired does not get a second life from the grace window.
  - Validation answers with the credential id, or raises a
    specific error: ``UnknownCredential`` for a stranger,
    ``ExpiredCredential`` for a known-but-dead one. Callers must
    be able to tell "wrong key" from "old key" without guessing.

Plain words: rotation is changing the locks while the shop is
open — new key in hand, old key honoured until closing, then
the old key is just metal.
"""

from datetime import timedelta

from problem_01_short_lived_credential import Credential


class CredentialError(ValueError):
    """Base error for credential validation failures."""


class UnknownCredential(CredentialError):
    """The presented secret matches no current or previous credential."""


class ExpiredCredential(CredentialError):
    """The presented secret matched a credential that is dead (expired or past grace)."""


class DualCredentialStore:
    """Holds a current credential plus, briefly, its predecessor."""

    def __init__(self, current):
        if not isinstance(current, Credential):
            raise CredentialError("current must be a Credential")
        self.current = current
        self.previous = None
        self._grace_until = None

    def rotate(self, new_credential, grace_seconds, now):
        """Install ``new_credential``; the old current becomes previous until grace ends."""
        if not isinstance(new_credential, Credential):
            raise CredentialError("new credential must be a Credential")
        if grace_seconds < 0:
            raise CredentialError(f"grace_seconds must be >= 0, got {grace_seconds!r}")
        self.previous = self.current
        self.current = new_credential
        self._grace_until = now + timedelta(seconds=grace_seconds)
        return self.current

    def validate(self, secret, now):
        """Return the credential id for a usable secret, or raise a specific error."""
        if secret == self.current.secret:
            if self.current.is_expired(now):
                raise ExpiredCredential(f"current credential {self.current.credential_id!r} expired")
            return self.current.credential_id
        if self.previous is not None and secret == self.previous.secret:
            if self.previous.is_expired(now):
                raise ExpiredCredential(f"previous credential {self.previous.credential_id!r} expired")
            if self._grace_until is not None and now > self._grace_until:
                raise ExpiredCredential(
                    f"previous credential {self.previous.credential_id!r} past grace period")
            return self.previous.credential_id
        raise UnknownCredential("secret matches no current or previous credential")
