"""Day 20 - Problem 2: Pickle is fast — and a loaded gun.

THE PROBLEM (beginner foothold first)
------------------------------------
``pickle`` serializes almost any Python object in one call, and
loads it back just as fast. It is the easiest cache format in
Python:

    >>> import pickle
    >>> pickle.loads(pickle.dumps({"a": 1}))   # {'a': 1}

The catch: unpickling RUNS CODE. A pickle is a little program,
and ``pickle.loads`` executes it. Loading bytes you did not
produce — from a queue, an upload, a cache you share — hands
the sender a shell on your machine.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The dangerous opcodes are GLOBAL / STACK_GLOBAL (import a
    name like ``os.system``) and REDUCE (call it). A benign
    dict pickle contains none of them.
  - ``pickletools.genops`` lets you SCAN a pickle's opcodes
    without executing anything — the safe way to inspect bytes
    before you decide to trust them.
  - Pickles also break across Python versions: a cache written
    on 3.8 may not load on 3.12. Never persist pickles across
    a deploy boundary.
  - The rule: pickle only inside ONE trusted process's cache.
    The moment bytes cross a trust boundary, they stop being
    data and start being code.

Your solution: ``trusted_roundtrip`` and ``scan_pickle_ops``
are already written. The tests prove a dict pickle is clean —
and that a crafted ``__reduce__`` payload lights up the scan
(the payload is only ever SCANNED, never loaded).

ANALOGY
-------
Pickle is the locked case only you have the key for. The
moment someone else hands you a locked case, assume it is
not empty — scan it before you open it.
"""
import io
import os
import pickle
import pickletools

DANGEROUS_OPS = {"GLOBAL", "STACK_GLOBAL", "REDUCE"}


def trusted_roundtrip(obj):
    """Pickle-roundtrip for data produced inside this trusted process."""
    return pickle.loads(pickle.dumps(obj))


def scan_pickle_ops(data):
    """Return [(opcode_name, arg)] for dangerous opcodes found in ``data``.

    Inspects with ``pickletools`` — never executes the payload.
    """
    found = []
    for opcode, arg, _pos in pickletools.genops(data):
        if opcode.name in DANGEROUS_OPS:
            found.append((opcode.name, arg))
    return found


class _Evil:
    """A payload whose __reduce__ would run a shell command ON LOAD.

    Used only to build bytes for the scanner test — it is never
    unpickled anywhere in this repo.
    """

    def __reduce__(self):
        return (os.system, ("echo pwned",))


def craft_malicious_pickle():
    """Build (not load) a pickle that executes code on unpickling."""
    return pickle.dumps(_Evil(), protocol=4)


if __name__ == "__main__":
    benign = pickle.dumps({"user_id": "u-7", "amount": 19.99})
    print("benign scan:", scan_pickle_ops(benign))
    print("malicious scan:", scan_pickle_ops(craft_malicious_pickle()))
    print("roundtrip:", trusted_roundtrip({"a": 1}))
