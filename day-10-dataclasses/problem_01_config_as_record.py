"""Problem 1 — Config as a record
===============================

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline's retry settings travel as a dict:

    cfg = {"max_attempts": 3, "backoff_s": 2.0}

Every stage reaches in with ``cfg["max_attempts"]`` — a string key that
typos love and IDEs can't see. Miss the key and you get a ``KeyError``;
rename it in one place and four others silently keep the old name.

``@dataclass`` turns the dict into a typed record: fields with defaults,
attribute access, and a repr that prints the whole config for free.

Plain words: the config stops being a bag of strings and becomes an
object with a shape.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Annotations DOCUMENT types; they don't ENFORCE them. Nothing stops
    ``RetryPolicy(max_attempts="three")`` at runtime — enforcement lives
    in ``__post_init__`` (Problem 4).
  - ``**raw`` unpacking forwards typos straight into the constructor,
    which is exactly the fail-fast you want — but only if you don't
    pre-filter with ``.get()`` and swallow the evidence first.
  - Defaults belong on the record, not scattered as ``cfg.get("x", d)``
    across five stages. One canonical default beats five copies that
    drift apart.

Your solution: ``build_retry(raw)`` — build a ``RetryPolicy`` from a
mapping. Missing keys take the dataclass defaults; unknown keys raise
``TypeError`` naming them. Non-mappings raise ``TypeError`` too.

Plain words: the constructor is the bouncer — the mapping doesn't get
in unless its keys are on the list.

ANALOGY
-------
The dict is a napkin with scribbles; the dataclass is the printed form
with labeled boxes. Same facts — the form refuses a mislabeled box.

YOUR TASK
---------
Implement ``build_retry`` below. Then run the tests:
``python -m pytest tests -q`` from the day-10 folder.
"""

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_s: float = 2.0

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_s < 0:
            raise ValueError("backoff_s must be >= 0")


_KNOWN = {f.name for f in fields(RetryPolicy)}


def build_retry(raw):
    """Build a RetryPolicy from a mapping; unknown keys raise TypeError."""
    if not isinstance(raw, dict):
        raise TypeError(f"expected a mapping, got {type(raw).__name__}")
    unknown = sorted(set(raw) - _KNOWN)
    if unknown:
        raise TypeError(f"unknown config keys: {unknown}")
    return RetryPolicy(**{k: v for k, v in raw.items() if k in _KNOWN})


if __name__ == "__main__":
    print(build_retry({"max_attempts": 5}))            # RetryPolicy(5, 2.0)
    print(build_retry({}))                             # defaults: (3, 2.0)
    try:
        build_retry({"max_attemps": 5})                # typo'd key
    except TypeError as e:
        print("rejected:", e)
