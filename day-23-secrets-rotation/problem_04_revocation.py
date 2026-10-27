"""Problem 4 — revocation: kill a leaked key now, not at its expiry
===================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Expiry is a deadline; revocation is an emergency stop. When a key
leaks, you cannot wait for its hotel-card checkout time — you
cancel the card right now, and every door must know. A revocation
list is that shared "cancelled cards" list: checked on every use,
not just at login, because a credential valid at 9 AM can be
leaked at 9:05.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Revocation is checked by credential id, never by secret
    value: the list must not store (or leak) the secret itself.
  - Revoking twice is not an error: the second call is a no-op
    that reports it changed nothing, and the FIRST revocation
    time and reason are kept — an audit trail must not be
    rewritten by a duplicate call.
  - A revoked credential stays revoked even if it has not
    expired: ``check`` raises ``RevokedCredential`` regardless
    of remaining lifetime. Expiry and revocation are two
    independent kill switches.
  - Bulk revocation reports how many were NEWLY revoked, so a
    "revoke everything for this service" sweep can prove what
    it actually changed.

Plain words: expiry is the card's checkout time; revocation is
calling the hotel the moment you lose the card. Both must work,
independently.
"""

from datetime import datetime, timezone


class RevokedCredential(ValueError):
    """Raised when a revoked credential is presented."""


class RevocationList:
    """The cancelled-cards list: ids, reasons, and first-revocation times."""

    def __init__(self):
        self._revoked = {}  # credential_id -> (revoked_at, reason)

    def revoke(self, credential_id, reason="compromised", now=None):
        """Revoke one id. Returns True if newly revoked, False if already revoked."""
        if not credential_id:
            raise ValueError("credential_id must be non-empty")
        if credential_id in self._revoked:
            return False
        now = now if now is not None else datetime.now(timezone.utc)
        self._revoked[credential_id] = (now, reason)
        return True

    def revoke_all(self, credential_ids, reason="compromised", now=None):
        """Revoke many ids. Returns the count newly revoked."""
        return sum(1 for cid in credential_ids if self.revoke(cid, reason=reason, now=now))

    def is_revoked(self, credential_id):
        return credential_id in self._revoked

    def check(self, credential_id):
        """Raise RevokedCredential if revoked; otherwise return silently."""
        if self.is_revoked(credential_id):
            revoked_at, reason = self._revoked[credential_id]
            raise RevokedCredential(
                f"credential {credential_id!r} revoked at {revoked_at.isoformat()} ({reason})")

    def revoked_ids(self):
        """Revoked ids in revocation order."""
        return list(self._revoked)

    def reason_for(self, credential_id):
        entry = self._revoked.get(credential_id)
        return entry[1] if entry else None
