"""Problem 2 — Fail at the door
============================

THE PROBLEM (beginner foothold first)
------------------------------------
``cfg.get("timeuot", 30)`` — spot the bug. The real key is ``timeout``,
but ``.get()`` with a default never complains: it silently hands back 30
for a key that was never spelled right anywhere. The typo survives to
production wearing a plausible value as camouflage.

A dataclass constructor does the opposite: an unexpected keyword is a
``TypeError`` on the spot. The strict builder below makes that rejection
explicit and names every offending key, so the error message IS the fix.

Plain words: ``.get()`` with a default is a typo laundering machine.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Silent-ignore vs loud-reject is a DESIGN choice, not a default.
    Libraries that "helpfully" drop unknown keys turn every typo into
    a config that looks right and behaves wrong.
  - When rejecting, list ALL unknown keys in one error, not just the
    first — the user fixes everything in one edit instead of playing
    whack-a-mole across five runs.
  - Sort the offending keys for deterministic messages; deterministic
    errors are greppable, and greppable errors get fixed at 2 AM.

Your solution: ``strict_build(cls, mapping)`` — construct any dataclass
``cls`` from a mapping. Unknown keys raise ``TypeError`` listing them
all (sorted). Non-mappings raise ``TypeError``.

Plain words: the door checks the guest list and reads back every name
that isn't on it.

ANALOGY
-------
``.get(key, default)`` is a bouncer who waves everyone through and hands
strangers a spare badge. ``strict_build`` checks the list out loud.

YOUR TASK
---------
Implement ``strict_build`` below. Then run the tests:
``python -m pytest tests -q`` from the day-10 folder.
"""

from dataclasses import fields


def strict_build(cls, mapping):
    """Build dataclass cls from mapping; unknown keys raise TypeError."""
    if not isinstance(mapping, dict):
        raise TypeError(f"expected a mapping, got {type(mapping).__name__}")
    known = {f.name for f in fields(cls)}
    unknown = sorted(set(mapping) - known)
    if unknown:
        raise TypeError(f"unknown keys for {cls.__name__}: {unknown}")
    return cls(**{k: v for k, v in mapping.items() if k in known})


if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Sink:
        table: str = "events"
        batch_size: int = 1000

    print(strict_build(Sink, {"table": "clicks"}))
    try:
        strict_build(Sink, {"table": "clicks", "batch_siez": 10})
    except TypeError as e:
        print("rejected:", e)
