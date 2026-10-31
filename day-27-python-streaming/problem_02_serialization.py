"""Problem 2 — the wire format is a contract, and contracts evolve.

THE PROBLEM (beginner foothold first)
------------------------------------
A producer writes events and a consumer reads them, but they are
rarely deployed at the same time. If the producer adds a field the
consumer does not know, or the consumer expects a field the producer
stopped sending, the pipeline should not crash — it should decide,
explicitly, what to do with the mismatch.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Every message is an envelope: a schema version plus a payload,
    encoded as UTF-8 JSON bytes. The version travels with the data,
    so a consumer can tell what it is looking at.
  - A version is registered with its required fields. Encoding a
    record missing a required field fails at the producer, never in
    the middle of a consumer's batch.
  - Decoding tolerates unknown fields (forward compatibility: a new
    producer field must not break an old consumer) and rejects a
    payload missing a required field for its version.
  - Decoding refuses what it cannot understand: bytes that are not
    JSON, envelopes missing version/payload, or a version newer than
    the reader supports — each raises, with a distinct error, so the
    caller can dead-letter it instead of silently dropping data.

Plain words: version the envelope, require what you need, ignore what
you don't know — and never guess at bytes you can't parse.
"""

import json


class SerializationError(ValueError):
    """Raised for a corrupt, malformed, or unparseable message."""


class SchemaError(ValueError):
    """Raised for a schema violation: missing field, unknown version."""


class SchemaRegistry:
    """Versioned JSON envelope schemas, stdlib only."""

    def __init__(self, max_supported_version):
        if not isinstance(max_supported_version, int) or max_supported_version < 1:
            raise SchemaError("max_supported_version must be a positive integer")
        self.max_supported_version = max_supported_version
        self._schemas = {}

    def register(self, version, required_fields):
        """Register ``version`` with its iterable of required fields."""
        if not isinstance(version, int) or version < 1:
            raise SchemaError("version must be a positive integer")
        if version > self.max_supported_version:
            raise SchemaError("cannot register a version newer than supported")
        self._schemas[version] = set(required_fields)

    def encode(self, record, version):
        """Encode ``record`` under ``version``; return UTF-8 bytes."""
        if version not in self._schemas:
            raise SchemaError(f"unregistered schema version: {version}")
        if not isinstance(record, dict):
            raise SchemaError("record must be a dict")
        missing = self._schemas[version] - set(record)
        if missing:
            raise SchemaError(f"missing required fields: {sorted(missing)}")
        envelope = {"v": version, "payload": record}
        return json.dumps(envelope, sort_keys=True).encode("utf-8")

    def decode(self, data):
        """Decode bytes; return ``(version, payload_dict)``.

        Unknown payload fields are kept (callers may ignore them);
        missing required fields, bad envelopes, and versions newer
        than supported all raise.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise SerializationError("message must be bytes")
        try:
            envelope = json.loads(bytes(data).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise SerializationError(f"message is not valid JSON: {exc}") from exc
        if not isinstance(envelope, dict) or "v" not in envelope or "payload" not in envelope:
            raise SerializationError("envelope must carry 'v' and 'payload'")
        version = envelope["v"]
        payload = envelope["payload"]
        if not isinstance(version, int) or version < 1:
            raise SerializationError(f"invalid schema version: {version!r}")
        if version > self.max_supported_version:
            raise SchemaError(f"version {version} is newer than supported")
        if version not in self._schemas:
            raise SchemaError(f"unregistered schema version: {version}")
        if not isinstance(payload, dict):
            raise SerializationError("payload must be an object")
        missing = self._schemas[version] - set(payload)
        if missing:
            raise SchemaError(f"missing required fields: {sorted(missing)}")
        return version, dict(payload)
