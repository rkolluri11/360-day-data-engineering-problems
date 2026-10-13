"""Problem 5 — The mutable-default trap
====================================

THE PROBLEM (beginner foothold first)
------------------------------------
``def __init__(self, name, inputs=[])`` — the default list is created
ONCE, when the function is defined, and shared by every instance that
doesn't pass ``inputs``. Stage A appends to "its" list and stage B finds
stage A's entries already there. The bug is silent, order-dependent,
and only shows up when two instances exist in one process — i.e.,
always in production, never in the unit test that builds one.

``field(default_factory=list)`` fixes it: the factory runs per
instance, so each record gets its own list.

Plain words: a bare ``[]`` default is a shared whiteboard; the factory
gives every instance its own notebook.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The trap applies to EVERY mutable default: ``[]``, ``{}``, ``set()``.
    Dataclasses refuse bare mutable defaults outright (``ValueError:
    mutable default ... use default_factory``) — the language is
    stricter here than plain functions, which is a feature.
  - ``default_factory`` takes a zero-argument callable: ``list``,
    ``dict``, ``set`` — or ``lambda`` / ``functools.partial`` for
    parameterized defaults like ``partial(dict, region="us")``.
  - The same aliasing bites with ``x = y = []`` and with default
    ARGUMENTS in plain functions. Train the reflex once: mutable
    default → factory, everywhere.

Your solution: ``SloppyStage`` (plain class, the bug: ``inputs=[]``
default) and ``Stage`` (dataclass with ``field(default_factory=list)``).
``shares_default(a, b)`` returns True when ``a.inputs is b.inputs`` —
the SAME list object. Tests prove the bug on ``SloppyStage`` and the
fix on ``Stage``, including a ``dict``-valued field via
``field(default_factory=dict)`` on ``TaggedStage``.

Plain words: prove the haunting, then exorcise it.

ANALOGY
-------
The shared default is the office fridge labeled "everyone's": whatever
you put in, someone else eats. The factory is a labeled lunchbox per
person.

YOUR TASK
---------
Implement the classes and ``shares_default`` below. Then run the tests:
``python -m pytest tests -q`` from the day-10 folder.
"""

from dataclasses import dataclass, field


class SloppyStage:
    """The bug: one list object shared by every default instance."""

    def __init__(self, name, inputs=[]):  # noqa: B006 — the trap, on purpose
        self.name = name
        self.inputs = inputs


@dataclass
class Stage:
    """The fix: each instance gets its own list."""

    name: str
    inputs: list = field(default_factory=list)


@dataclass
class TaggedStage:
    """Same trap, dict flavor — also fixed by a factory."""

    name: str
    tags: dict = field(default_factory=dict)


def shares_default(a, b):
    """True when a.inputs IS b.inputs — the same list object."""
    return a.inputs is b.inputs


if __name__ == "__main__":
    s1, s2 = SloppyStage("a"), SloppyStage("b")
    s1.inputs.append("leak")
    print("sloppy shares:", shares_default(s1, s2), "| s2 sees:", s2.inputs)

    f1, f2 = Stage("a"), Stage("b")
    f1.inputs.append("ok")
    print("fixed shares:", shares_default(f1, f2), "| f2 sees:", f2.inputs)
