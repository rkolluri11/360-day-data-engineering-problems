"""Problem 2 — The cache that leaked between functions
=================================================

THE PROBLEM (beginner foothold first)
------------------------------------
In Python, a default argument like ``cache={}`` is created **once**,
when the function is defined — not each time the function is called.
Every call shares the same dictionary.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A retry decorator caches the last result of the function it wraps so a
flaky API call can be retried from the cache:

    @retry_with_cache()
    def fetch_orders(): ...

    @retry_with_cache()
    def fetch_customers(): ...

With a mutable default argument as the cache, ``fetch_orders`` and
``fetch_customers`` **share one cache**. A failed customers call can
return cached orders. Fix ``retry_with_cache`` so each decorated
function gets its own private cache.

Plain words: the buggy version puts every function's lunch in one
shared fridge with no names on the bags. The fix gives each function
its own fridge the moment it is decorated.

ANALOGY
-------
Default arguments are engraved at definition time, like a nameplate on
a desk — everyone who sits there later shares the same drawer.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional


def retry_with_cache(cache: Optional[dict] = None) -> Callable:
    """Decorator giving each decorated function its own result cache.

    The first call's result is cached; a later call whose function
    raises returns the cached result instead (a simple retry-from-cache
    strategy).
    """
    if cache is None:
        cache = {}  # fresh fridge per decorated function

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            try:
                result = fn(*args, **kwargs)
            except Exception:
                if key in cache:
                    return cache[key]
                raise
            cache[key] = result
            return result

        return wrapper

    return decorator


if __name__ == "__main__":

    @retry_with_cache()
    def fetch_orders() -> list:
        return ["order-1"]

    @retry_with_cache()
    def fetch_customers() -> list:
        raise RuntimeError("flaky API")

    print(fetch_orders())
    # This must raise — customers has its own empty cache, not orders'.
    try:
        fetch_customers()
    except RuntimeError as exc:
        print(f"correctly raised, no leak: {exc}")
