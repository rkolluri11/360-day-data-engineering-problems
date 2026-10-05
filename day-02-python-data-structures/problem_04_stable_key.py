"""Problem 4 — The cache key that couldn't hold its shape
========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
You want to cache the result of an expensive pipeline step so the
same call never runs twice:

    @keyed_cache
    def fetch_report(filters, columns=("a", "b")): ...

Write ``keyed_cache`` — a decorator that remembers results keyed by
the call's arguments. Same arguments, same objects or equal-but-
different objects: the function must run exactly once.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Pipeline arguments are dicts and lists — unhashable, so they can't be
dict keys, and ``functools.lru_cache`` raises ``TypeError`` on them.
Worse, ``{"a": 1, "b": 2}`` and ``{"b": 2, "a": 1}`` are the same
filters and must hit the same cache entry. Build ``stable_key(*args,
**kwargs)``: a hashable, canonical key where unhashable values are
frozen recursively (lists to tuples, dicts to sorted key/value
tuples, sets to frozensets) and kwarg order is normalized away.
``keyed_cache`` then uses it. The key must never mutate under you —
freeze at call time, not by reference.

Plain words: before filing the request in the labeled drawer, press
the wobbly jelly arguments into a solid, always-the-same-shape ice
cube — then the drawer label never lies.

ANALOGY
-------
A coat check that tags your bag by its exact shape, not by the bag
itself: two identical bags get the same tag, and the tag can't
change while your bag hangs there.
"""

from __future__ import annotations

import functools


def _freeze(value):
    """Recursively convert a value into a hashable, canonical form."""
    if isinstance(value, dict):
        return tuple(
            (key, _freeze(val))
            for key, val in sorted(value.items(), key=lambda kv: repr(kv[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def stable_key(*args, **kwargs):
    """Build a hashable, canonical cache key from call arguments.

    Equal-valued args (even distinct objects, even unhashable ones)
    produce equal keys; kwarg order is ignored.
    """
    frozen_args = tuple(_freeze(arg) for arg in args)
    frozen_kwargs = tuple(
        (name, _freeze(value))
        for name, value in sorted(kwargs.items(), key=lambda kv: kv[0])
    )
    return (frozen_args, frozen_kwargs)


def keyed_cache(func):
    """Memoize ``func`` on its arguments, tolerating unhashable ones.

    Results are stored in a plain dict keyed by ``stable_key(...)``.
    Exposes ``cache_clear()`` to reset.
    """
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = stable_key(*args, **kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache_clear = cache.clear
    return wrapper


if __name__ == "__main__":
    calls = {"n": 0}

    @keyed_cache
    def fetch_report(filters, columns=("a", "b")):
        calls["n"] += 1
        return {"rows": len(filters)}

    # Same filters, different objects and kwarg order — one real call.
    fetch_report({"region": "eu", "tags": ["x"]}, columns=["a", "b"])
    fetch_report({"tags": ["x"], "region": "eu"}, columns=("a", "b"))
    print("real calls:", calls["n"])  # 1
