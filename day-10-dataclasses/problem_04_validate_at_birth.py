"""Problem 4 — Validate at birth
==============================

THE PROBLEM (beginner foothold first)
------------------------------------
``batch_size=0`` sails through the config loader, the extractor, and the
transform — then the loader divides by it, or the sink writes empty
files for six hours. The invalid value was knowable at line one and
fatal at line ten thousand.

``__post_init__`` runs right after the dataclass constructor: check
ranges, enums, and formats there, and a bad record can never exist.
Raising works even on frozen classes — validation happens before the
freeze matters.

Plain words: check the passport at birth, not at the border crossing
six hours later.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Validate VALUES, not just presence: ``batch_size`` exists AND is
    positive; ``level`` exists AND is a known level. Presence checks
    alone let ``batch_size=-5`` through.
  - Raise ``ValueError`` (or a domain subclass), never ``AssertionError``:
    asserts can be stripped with ``python -O``; your validation must
    survive production flags.
  - One record, one error surface: when several fields are wrong, the
    FIRST failure wins — keep messages specific enough that the fix is
    obvious ("batch_size must be >= 1, got 0").

Your solution: ``BatchConfig`` — a frozen dataclass with fields
``table: str`` (required), ``batch_size: int = 1000``,
``level: str = "INFO"``. In ``__post_init__``: ``table`` must match
``^[a-z_]+$``; ``batch_size >= 1``; ``level`` in
``{"DEBUG", "INFO", "WARN", "ERROR"}``. Violations raise ``ValueError``.

Plain words: a BatchConfig that exists is a BatchConfig that's sane.

ANALOGY
-------
``__post_init__`` is the hospital wristband check: name, weight, and
blood type verified before the baby leaves the room — not discovered
missing at the first checkup.

YOUR TASK
---------
Implement ``BatchConfig`` below. Then run the tests:
``python -m pytest tests -q`` from the day-10 folder.
"""

import re
from dataclasses import dataclass

_TABLE = re.compile(r"^[a-z_]+$")
_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR"}


@dataclass(frozen=True)
class BatchConfig:
    table: str
    batch_size: int = 1000
    level: str = "INFO"

    def __post_init__(self):
        if not isinstance(self.table, str) or not _TABLE.match(self.table):
            raise ValueError(
                f"table must match ^[a-z_]+$, got {self.table!r}"
            )
        if not isinstance(self.batch_size, int) or self.batch_size < 1:
            raise ValueError(
                f"batch_size must be >= 1, got {self.batch_size!r}"
            )
        if self.level not in _LEVELS:
            raise ValueError(
                f"level must be one of {sorted(_LEVELS)}, got {self.level!r}"
            )


if __name__ == "__main__":
    print(BatchConfig("events"))                       # defaults kick in
    print(BatchConfig("clicks", batch_size=500, level="WARN"))
    for bad in ({"table": "Events"},
                {"table": "events", "batch_size": 0},
                {"table": "events", "level": "LOUD"}):
        try:
            BatchConfig(**bad)
        except ValueError as e:
            print("rejected:", e)
