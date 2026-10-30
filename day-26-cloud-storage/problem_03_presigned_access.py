"""Problem 3 — presigned access: hand out a key that expires, not the vault.

THE PROBLEM (beginner foothold first)
------------------------------------
A partner needs one file for one hour. Handing them the bucket
credentials gives them every file forever; emailing the file gives
them a stale copy. A presigned URL bakes the permission into one link
— this object, this operation, until this time — and then it stops
working on its own.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The signature covers bucket, key, method, and expiry together:
    changing any one of them after signing must invalidate the link,
    so a GET link cannot be rewritten into a PUT link or pointed at a
    different object.
  - Expiry is enforced at validation time against the validator's
    clock: a link used one second past expiry is dead, not "close".
  - The method in the request must match the method that was signed;
    a signed GET does not authorize a DELETE.
  - Revocation is explicit: once a signature is revoked, validation
    fails even inside its window — expiry alone is not the only off
    switch.
  - Signing with a different secret than validation must fail: the
    signature is only as trustworthy as the secret that made it.

Plain words: a presigned URL is a hotel key card — it opens one room,
it stops working at checkout, and the front desk can deactivate it
early. It is never a copy of the master key.
"""

import hashlib
import hmac
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


class PresignError(ValueError):
    """Raised for an invalid presign request (bad method, bad expiry)."""


_METHODS = ("GET", "PUT", "DELETE", "HEAD")


def _signature(secret, bucket, key, method, expires):
    message = f"{method}\n{bucket}\n{key}\n{expires}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message,
                    hashlib.sha256).hexdigest()


class Presigner:
    """Sign and validate expiring, single-object, single-method URLs."""

    def __init__(self, secret):
        if not secret:
            raise PresignError("a non-empty secret is required")
        self._secret = secret
        self._revoked = set()

    def sign(self, bucket, key, method, expires_in_seconds, now):
        """Return a presigned URL valid until ``now + expires_in``.

        ``now`` and expiry are plain integer seconds, so tests never
        touch the wall clock. ``expires_in_seconds`` must be positive.
        """
        if method not in _METHODS:
            raise PresignError(f"unsupported method: {method!r}")
        if not isinstance(expires_in_seconds, int) \
                or isinstance(expires_in_seconds, bool) \
                or expires_in_seconds <= 0:
            raise PresignError("expires_in_seconds must be a positive int")
        expires = now + expires_in_seconds
        sig = _signature(self._secret, bucket, key, method, expires)
        query = urlencode({"method": method, "expires": expires, "sig": sig})
        return urlunparse(("https", f"{bucket}.storage.example",
                           f"/{key}", "", query, ""))

    def revoke(self, url):
        """Revoke a signed URL by its signature, even inside its window."""
        self._revoked.add(_sig_of(url))

    def validate(self, url, method, now):
        """Return True only if ``url`` authorizes ``method`` right now.

        False covers every failure mode — expired, tampered,
        wrong-secret, revoked, malformed, or method mismatch — so a
        caller can treat any False as "deny" without parsing reasons.
        """
        try:
            parsed = urlparse(url)
            bucket = parsed.netloc.split(".storage.example")[0]
            key = parsed.path.lstrip("/")
            params = parse_qs(parsed.query)
            signed_method = params["method"][0]
            expires = int(params["expires"][0])
            sig = params["sig"][0]
        except (IndexError, KeyError, ValueError):
            return False
        if method != signed_method:
            return False
        if now >= expires:
            return False
        if sig in self._revoked:
            return False
        expected = _signature(self._secret, bucket, key, signed_method,
                              expires)
        return hmac.compare_digest(expected, sig)


def _sig_of(url):
    return parse_qs(urlparse(url).query).get("sig", [""])[0]
