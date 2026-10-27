"""Problem 3 — the rotation schedule: rotate before it hurts, not after
=========================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Waiting until a key expires to replace it is waiting until the
shop is locked out to cut a new key. Healthy pipelines rotate
EARLY: when the remaining life drops below a lead time, rotation
is due — even though the credential still works. The old one then
has a runway to drain while the new one takes over (Problem 2's
grace window), instead of a cliff edge at midnight.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Two numbers, both enforced: ``max_age_seconds`` caps how
    long any credential may live, and ``rotate_lead_seconds``
    says how early rotation must start. A lead larger than the
    max age is a configuration bug — rejected at construction,
    not discovered at 2 AM.
  - ``next_rotation_at`` is derived, not stored: expiry minus
    the lead. If anyone changes the credential, the schedule
    follows automatically.
  - ``is_due`` is a pure function of credential + time, so a
    scheduler, a health check, and a test all agree on whether
    rotation is due. No hidden state, no "it rotated yesterday
    so it must be fine".
  - ``is_overdue`` is separate from ``is_due``: due means "rotate
    soon", overdue means "already expired and still in use" —
    the incident, not the warning.

Plain words: rotate the key while it still works, with time to
spare — the way you replace a tyre before it blows, not after.
"""

from datetime import timedelta


class RotationPolicyError(ValueError):
    """Raised for an impossible rotation policy (e.g. lead longer than max age)."""


class RotationPolicy:
    """When a credential must be rotated, derived from its own expiry."""

    def __init__(self, max_age_seconds, rotate_lead_seconds):
        if max_age_seconds <= 0:
            raise RotationPolicyError(f"max_age_seconds must be positive, got {max_age_seconds!r}")
        if rotate_lead_seconds < 0:
            raise RotationPolicyError(f"rotate_lead_seconds must be >= 0, got {rotate_lead_seconds!r}")
        if rotate_lead_seconds > max_age_seconds:
            raise RotationPolicyError(
                f"rotate_lead_seconds ({rotate_lead_seconds}) exceeds "
                f"max_age_seconds ({max_age_seconds})")
        self.max_age_seconds = max_age_seconds
        self.rotate_lead_seconds = rotate_lead_seconds

    def next_rotation_at(self, credential):
        """The moment rotation becomes due for this credential."""
        return credential.expires_at - timedelta(seconds=self.rotate_lead_seconds)

    def is_due(self, credential, now):
        """True once remaining life is at or below the lead time."""
        return now >= self.next_rotation_at(credential)

    def is_overdue(self, credential, now):
        """True only once the credential has actually expired."""
        return credential.is_expired(now)

    def seconds_until_due(self, credential, now):
        """Seconds until rotation is due (negative once due)."""
        return (self.next_rotation_at(credential) - now).total_seconds()
