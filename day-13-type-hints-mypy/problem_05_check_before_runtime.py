"""Problem 5 — check before runtime: a mini-mypy for stage boundaries
=======================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Hints are metadata — Python ignores them at runtime (problem 1 proved it).
So who enforces the contract? mypy: a static checker that reads the hints
and fails the BUILD, so the type error dies in CI instead of at 2 AM.

This problem builds a tiny version of that gate: ``check_call`` binds the
arguments to the signature, validates each one against the annotation, and
only then calls the function. Wrong types raise ``HintViolation`` with a
mypy-style message — the same shape of error, caught at the boundary.

Plain words: ``check_call`` is the bouncer with the guest list (the hints).
No name on the list, no entry — before the party (the function body) starts.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``inspect.signature(fn).bind(*args, **kwargs)`` maps arguments to
    parameter names — including defaults via ``apply_defaults()``. The
    check sees what the function sees.
  - ``typing.get_type_hints`` resolves the annotations to real objects;
    the matcher handles plain classes (isinstance), unions (``str | None``
    — any branch may match), and generic aliases (``list[dict]`` checks
    the origin). Unknown constructs don't block: a checker that cries
    wolf on every exotic hint gets deleted.
  - Check at the BOUNDARY, not everywhere: stage entry points, API
    handlers, anything another team calls. Inside a checked boundary,
    plain calls stay fast.
  - ``HintViolation`` subclasses ``TypeError`` — it IS a type error, so
    existing ``except TypeError`` handling still catches it.

Your solution: ``check_call`` (validate-then-call) and ``check_return``
(validate a produced value against the ``->`` annotation). Then run the
tests: ``python -m pytest tests -q`` from the day-13 folder.

ANALOGY
-------
mypy is the spell-checker that runs before you hit send. You could
proofread every email by hand (read every call site), or let the checker
underline the mistakes while you still have time to fix them.
"""

import inspect
import types
import typing
from typing import get_type_hints


class HintViolation(TypeError):
    """A type-contract violation caught at the boundary, mypy-style."""


def _name(hint) -> str:
    s = str(hint).replace("typing.", "")
    if s.startswith("<class "):
        return getattr(hint, "__name__", s)
    return s


def _matches(value, hint) -> bool:
    """Does ``value`` satisfy the annotation ``hint``?"""
    if hint is None or hint is type(None):
        return value is None
    if isinstance(hint, types.UnionType) or typing.get_origin(hint) is typing.Union:
        return any(_matches(value, arg) for arg in typing.get_args(hint))
    origin = typing.get_origin(hint)
    if origin is not None:
        return isinstance(value, origin)
    if isinstance(hint, type):
        return isinstance(value, hint)
    return True  # exotic constructs: don't block, don't cry wolf


def check_call(fn, *args, **kwargs):
    """Validate arguments against fn's annotations, then call it.

    Raises HintViolation naming the offending parameter, mypy-style:
    'Argument "a" has incompatible type "str"; expected "float"'.
    """
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    for name, value in bound.arguments.items():
        if name in hints and not _matches(value, hints[name]):
            raise HintViolation(
                f'Argument "{name}" has incompatible type '
                f'"{type(value).__name__}"; expected "{_name(hints[name])}"'
            )
    return fn(*args, **kwargs)


def check_return(fn, value):
    """Validate a produced value against fn's ``->`` annotation."""
    hints = get_type_hints(fn)
    if "return" in hints and not _matches(value, hints["return"]):
        raise HintViolation(
            f'Return has incompatible type "{type(value).__name__}"; '
            f'expected "{_name(hints["return"])}"'
        )
    return value


def add_amounts(a: float, b: float) -> float:
    """Demo stage: add two amounts."""
    return a + b


def greet(name: str | None) -> str:
    """Demo stage: greet, handling the absent name."""
    return f"hi {name}" if name else "hi there"


if __name__ == "__main__":
    print("checked call:", check_call(add_amounts, 1.0, 2.0))
    print("none allowed:", check_call(greet, None))
    try:
        check_call(add_amounts, "1", 2.0)
    except HintViolation as e:
        print("caught at the boundary:", e)
