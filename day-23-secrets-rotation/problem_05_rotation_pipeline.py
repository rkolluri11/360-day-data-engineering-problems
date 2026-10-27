"""Problem 5 — the rotation pipeline end to end: fetch, fail, rotate, retry once
=================================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
All four earlier problems meet in one pipeline step: fetch with
the current credential; if it is due for rotation, rotate first;
if the service rejects it anyway, rotate once and retry once —
then stop. A pipeline that retries forever with a dead key, or
retries with a revoked key, turns a small outage into a lockout
(or an account ban). Exactly one retry, with a fresh key, is the
discipline.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Rotation before fetch when due: if the policy says rotation
    is due (Problem 3), the pipeline rotates BEFORE calling the
    service — it does not waste a request on a credential it
    already knows is about to die.
  - Exactly one auth retry: a fetch raising ``AuthError`` triggers
    one rotation and one retry. A second ``AuthError`` propagates
    — no infinite loop, no hammering the service.
  - Revoked is terminal: if the current credential is revoked
    (Problem 4), the fetch never runs and no retry can save it —
    ``RevokedCredential`` propagates immediately.
  - The provider is injected, not hardcoded: ``SimpleProvider``
    below is the demo (a queue of pre-made credentials); a real
    provider would call a vault. The pipeline never invents a
    credential itself, so it can never "rotate" to a guess.
  - Rotation count is observable: ``rotations`` tells an
    operator (and a test) exactly how many rotations happened,
    so a runaway rotation loop is visible, not folklore.

Plain words: try the key, and if the door says no, cut one new
key and try once more — then stop knocking and call for help.
"""

from problem_01_short_lived_credential import Credential
from problem_03_rotation_schedule import RotationPolicy
from problem_04_revocation import RevocationList, RevokedCredential


class AuthError(Exception):
    """The service rejected the presented credential (expired, wrong, or stale)."""


class SimpleProvider:
    """Demo credential provider: hands out pre-made credentials in order."""

    def __init__(self, credentials):
        if not credentials:
            raise ValueError("provider needs at least one credential")
        self._queue = list(credentials)
        self.current_credential = self._queue.pop(0)
        self.rotations = 0

    def rotate(self, now=None):
        if not self._queue:
            raise AuthError("no fresh credential available to rotate to")
        self.current_credential = self._queue.pop(0)
        self.rotations += 1
        return self.current_credential


class RotatingFetcher:
    """Fetch with rotation discipline: rotate-when-due, one auth retry, revoked is terminal."""

    def __init__(self, provider, policy, revocations):
        if not isinstance(policy, RotationPolicy):
            raise ValueError("policy must be a RotationPolicy")
        if not isinstance(revocations, RevocationList):
            raise ValueError("revocations must be a RevocationList")
        self.provider = provider
        self.policy = policy
        self.revocations = revocations

    def _current_or_raise(self, now):
        credential = self.provider.current_credential
        self.revocations.check(credential.credential_id)
        return credential

    def fetch(self, fetch_fn, now):
        """Call ``fetch_fn(credential)`` with rotation discipline. Returns its result."""
        credential = self._current_or_raise(now)
        if self.policy.is_due(credential, now) or credential.is_expired(now):
            credential = self.provider.rotate(now)
            self.revocations.check(credential.credential_id)
        try:
            return fetch_fn(credential)
        except AuthError:
            # One rotation, one retry — then stop.
            credential = self.provider.rotate(now)
            self.revocations.check(credential.credential_id)
            return fetch_fn(credential)
