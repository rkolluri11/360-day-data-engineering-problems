"""Day 23 tests — secrets handling and credential rotation patterns.

No network, no wall-clock, no real secrets: every time is an explicit
datetime, every credential value is a test string. stdlib only.
"""
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from problem_01_short_lived_credential import Credential, CredentialError
from problem_02_rotate_without_downtime import (
    DualCredentialStore, ExpiredCredential, UnknownCredential,
)
from problem_03_rotation_schedule import RotationPolicy, RotationPolicyError
from problem_04_revocation import RevocationList, RevokedCredential
from problem_05_rotation_pipeline import (
    AuthError, RotatingFetcher, SimpleProvider,
)

T0 = datetime(2026, 10, 26, 19, 30, tzinfo=timezone.utc)


def cred(cid, secret, ttl=3600, issued_at=T0):
    return Credential(cid, secret, issued_at, ttl)


# --- Problem 1: short-lived credentials -------------------------------------

def test_expiry_is_issued_plus_ttl_and_valid_before_it():
    c = cred("k1", "s1")
    assert c.expires_at == T0 + timedelta(seconds=3600)
    assert c.is_valid(T0 + timedelta(seconds=3599))
    assert c.seconds_remaining(T0) == 3600


def test_expired_at_and_after_expiry():
    c = cred("k1", "s1")
    assert c.is_expired(c.expires_at)
    assert c.is_expired(T0 + timedelta(hours=2))
    assert not c.is_valid(T0 + timedelta(hours=2))


def test_forever_is_rejected_and_naive_time_is_rejected():
    with pytest.raises(CredentialError):
        Credential("k1", "s1", T0, 0)
    with pytest.raises(CredentialError):
        Credential("k1", "s1", datetime(2026, 10, 26, 19, 30), 3600)


def test_repr_never_leaks_the_secret():
    assert "s1" not in repr(cred("k1", "s1"))
    assert "***" in repr(cred("k1", "s1"))


# --- Problem 2: rotate without downtime --------------------------------------

def test_current_validates_and_stranger_is_unknown():
    store = DualCredentialStore(cred("old", "old-secret"))
    assert store.validate("old-secret", T0) == "old"
    with pytest.raises(UnknownCredential):
        store.validate("nope", T0)


def test_previous_valid_during_grace_and_dead_after_it():
    store = DualCredentialStore(cred("old", "old-secret"))
    store.rotate(cred("new", "new-secret"), grace_seconds=600, now=T0)
    assert store.validate("old-secret", T0 + timedelta(seconds=600)) == "old"
    assert store.validate("new-secret", T0) == "new"
    with pytest.raises(ExpiredCredential):
        store.validate("old-secret", T0 + timedelta(seconds=601))


def test_previous_expired_credential_gets_no_second_life_from_grace():
    store = DualCredentialStore(cred("old", "old-secret", ttl=60))
    store.rotate(cred("new", "new-secret"), grace_seconds=3600, now=T0)
    with pytest.raises(ExpiredCredential):
        store.validate("old-secret", T0 + timedelta(seconds=120))


def test_second_rotation_does_not_resurrect_the_first_credential():
    store = DualCredentialStore(cred("v1", "s-v1"))
    store.rotate(cred("v2", "s-v2"), grace_seconds=3600, now=T0)
    store.rotate(cred("v3", "s-v3"), grace_seconds=3600, now=T0)
    with pytest.raises(UnknownCredential):
        store.validate("s-v1", T0)


# --- Problem 3: rotation schedule --------------------------------------------

def test_next_rotation_is_expiry_minus_lead_and_due_at_that_moment():
    policy = RotationPolicy(max_age_seconds=3600, rotate_lead_seconds=300)
    c = cred("k1", "s1")
    assert policy.next_rotation_at(c) == T0 + timedelta(seconds=3300)
    assert not policy.is_due(c, T0 + timedelta(seconds=3299))
    assert policy.is_due(c, T0 + timedelta(seconds=3300))
    assert policy.seconds_until_due(c, T0) == 3300


def test_overdue_means_expired_not_merely_due():
    policy = RotationPolicy(max_age_seconds=3600, rotate_lead_seconds=300)
    c = cred("k1", "s1")
    assert not policy.is_overdue(c, T0 + timedelta(seconds=3300))
    assert policy.is_overdue(c, T0 + timedelta(seconds=3601))


def test_lead_longer_than_max_age_is_a_config_bug():
    with pytest.raises(RotationPolicyError):
        RotationPolicy(max_age_seconds=3600, rotate_lead_seconds=3601)


# --- Problem 4: revocation ----------------------------------------------------

def test_revoke_is_idempotent_and_keeps_the_first_reason():
    lst = RevocationList()
    assert lst.revoke("k1", reason="leaked", now=T0) is True
    assert lst.revoke("k1", reason="other", now=T0) is False
    assert lst.reason_for("k1") == "leaked"
    assert lst.is_revoked("k1") and not lst.is_revoked("k2")


def test_revoked_stays_revoked_even_before_expiry():
    lst = RevocationList()
    lst.revoke("k1", now=T0)
    with pytest.raises(RevokedCredential):
        lst.check("k1")
    lst.check("k2")  # unrevoked: no error


def test_revoke_all_counts_only_new_revocations():
    lst = RevocationList()
    lst.revoke("k1", now=T0)
    assert lst.revoke_all(["k1", "k2", "k3"], now=T0) == 2
    assert lst.revoked_ids() == ["k1", "k2", "k3"]


# --- Problem 5: rotation pipeline ----------------------------------------------

def _fetcher_for(credentials, lead=300):
    provider = SimpleProvider(credentials)
    policy = RotationPolicy(max_age_seconds=3600, rotate_lead_seconds=lead)
    return RotatingFetcher(provider, policy, RevocationList()), provider


def test_fetch_succeeds_without_rotation_when_not_due():
    fetcher, provider = _fetcher_for([cred("k1", "s1")])
    assert fetcher.fetch(lambda c: f"ok:{c.credential_id}", T0) == "ok:k1"
    assert provider.rotations == 0


def test_fetch_rotates_before_fetch_when_due():
    fetcher, provider = _fetcher_for([cred("k1", "s1"), cred("k2", "s2")])
    due = T0 + timedelta(seconds=3300)
    assert fetcher.fetch(lambda c: c.credential_id, due) == "k2"
    assert provider.rotations == 1


def test_auth_failure_rotates_once_and_retries_once():
    fetcher, provider = _fetcher_for([cred("k1", "s1"), cred("k2", "s2")])

    def flaky(c):
        if c.credential_id == "k1":
            raise AuthError("stale key")
        return "recovered"

    assert fetcher.fetch(flaky, T0) == "recovered"
    assert provider.rotations == 1


def test_second_auth_failure_propagates_instead_of_looping():
    fetcher, provider = _fetcher_for([cred("k1", "s1"), cred("k2", "s2")])

    def always_no(c):
        raise AuthError("rejected")

    with pytest.raises(AuthError):
        fetcher.fetch(always_no, T0)
    assert provider.rotations == 1  # exactly one retry rotation, then stop


def test_revoked_credential_never_reaches_the_service():
    provider = SimpleProvider([cred("k1", "s1")])
    revocations = RevocationList()
    revocations.revoke("k1", now=T0)
    fetcher = RotatingFetcher(provider, RotationPolicy(3600, 300), revocations)
    with pytest.raises(RevokedCredential):
        fetcher.fetch(lambda c: (_ for _ in ()).throw(AssertionError("must not run")), T0)
