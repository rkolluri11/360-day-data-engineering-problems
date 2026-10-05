"""Problem 4 — The dedup that worked in dev, failed in prod
=========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``==`` asks "do these have the same value?". ``is`` asks "are these the
exact same object in memory?". Python sometimes reuses one object for
equal strings (called *interning*), but only as an optimization — you
can never rely on it.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A config loader dedups environment names with identity:

    seen = []
    for env in environments:          # "dev", "staging", "prod", ...
        if not any(env is s for s in seen):
            seen.append(env)

In dev the names are string literals — interned, so ``is`` happens to
work and tests pass. In prod the names come from a YAML file, are
different objects, ``is`` fails, and every environment is processed
twice — double-running expensive jobs. Fix ``dedupe`` to compare by
value, in O(n) time.

Plain words: ``is`` checks whether two name tags are the same physical
tag; ``==`` checks whether they say the same words. The loader must
compare the words, because in production every tag is printed fresh.

ANALOGY
-------
Two identical house keys cut at different shops open the same door
(``==``), but they are not the same physical key (``is``). A lock that
only accepts "the same physical key" breaks the moment you get a copy.
"""

from __future__ import annotations


def dedupe(items: list[str]) -> list[str]:
    """Remove duplicates by value, preserving first-seen order (O(n))."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:  # ``in`` on a set uses == under the hood
            seen.add(item)
            out.append(item)
    return out


if __name__ == "__main__":
    # Simulate prod: names freshly built at runtime (never interned).
    envs = ["".join(list("dev")), "".join(list("staging")),
            "".join(list("dev")), "".join(list("prod"))]
    print(dedupe(envs))  # ['dev', 'staging', 'prod']
