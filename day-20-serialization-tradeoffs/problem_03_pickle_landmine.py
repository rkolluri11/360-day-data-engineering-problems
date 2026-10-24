"""Day 20 - Problem 3: never unpickle a stranger's bytes.

The hard problem: ``pickle.loads`` doesn't just read data — it RUNS
code. A pickled object can carry a ``__reduce__`` that executes
anything when unpickled, so a pickle payload off the network, off
disk, or out of a queue is remote code execution waiting for a
reader. The fix has two parts: sniff the magic bytes so you know what
arrived, and route pickle through a gate that refuses it by default.
The dangerous thing stays opt-in and loud, never a default.
"""
import json
import pickle


class PickleRefusedError(ValueError):
    """Raised when a pickle payload arrives and nobody vouched for it."""


EXECUTED = []  # the demo's canary: unpickling appends here


def _canary_hit(marker):
    """Stands in for attacker code — runs at ``loads()`` time."""
    EXECUTED.append(marker)


class _Canary:
    """A payload whose __reduce__ executes code on unpickle."""

    def __reduce__(self):
        return (_canary_hit, ("pwned-by-pickle",))


def make_malicious_pickle():
    """Build a payload that executes code the moment ``pickle.loads``
    touches it. In production this would be ``os.system``; here the
    canary list proves the point without the blast radius."""
    return pickle.dumps(_Canary())


def sniff_format(payload):
    """Identify a payload by its magic bytes, before trusting it."""
    if payload.startswith(b"\x80"):
        # pickle protocol 2+ frame header: version byte follows 0x80
        return "pickle"
    stripped = payload.lstrip()
    if stripped[:1] in (b"{", b"["):
        return "json"
    if payload.startswith(b"Obj\x01"):
        # avro object container file magic
        return "avro"
    if payload.startswith(b"PAR1"):
        # parquet magic (opens and closes every file)
        return "parquet"
    return "unknown"


def safe_deserialize(payload, allow_pickle=False):
    """Decode a boundary payload sniffed by magic bytes.

    JSON decodes normally. Pickle raises ``PickleRefusedError`` unless
    ``allow_pickle=True`` is passed explicitly — the only door pickle
    gets, opened on purpose, in code review. Anything else needs an
    explicit decoder; the gate never guesses.
    """
    kind = sniff_format(payload)
    if kind == "pickle" and not allow_pickle:
        raise PickleRefusedError(
            "refusing to unpickle: boundary bytes are never trusted. "
            "Pass allow_pickle=True only for same-process, same-trust "
            "bytes you created yourself."
        )
    if kind == "json":
        return json.loads(payload)
    if kind == "pickle":  # explicitly allowed above
        return pickle.loads(payload)
    raise ValueError("no safe decoder for %r payloads" % (kind,))


if __name__ == "__main__":
    evil = make_malicious_pickle()
    print("sniffed as:", sniff_format(evil))
    print("sniffed as:", sniff_format(b'{"order_id": "o-1"}'))
    try:
        safe_deserialize(evil)
    except PickleRefusedError as exc:
        print("gate refused:", exc)
    EXECUTED.clear()
    safe_deserialize(evil, allow_pickle=True)
    print("explicit opt-in ran the payload; canary:", EXECUTED)
