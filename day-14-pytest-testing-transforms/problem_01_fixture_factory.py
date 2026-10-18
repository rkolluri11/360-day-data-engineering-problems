"""Problem 1 — the fixture factory: fresh data for every test
============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Every transform test needs input rows. The lazy way is a module-level
dict that every test shares:

    BATCH = [{"order_id": "o-1", "amount": "10.00", "status": "paid"}]

Then test A appends a row, and test B — running after A — sees a batch
it never asked for. Tests pass alone and fail together, the worst kind
of flake. A *factory* (in pytest, a ``@pytest.fixture``) builds a FRESH
batch every time a test asks for one:

    @pytest.fixture
    def batch():
        return fresh_batch()   # new list, new dicts, every test

Plain words: a fixture is a mise en place station. Every chef (test)
gets a fresh tray of ingredients; nobody cooks from yesterday's
leftovers.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Shared MUTABE state between tests is the #1 source of order-dependent
    failures. ``fresh_batch()`` must return new objects, not references
    to one canonical list — mutating the result must never leak.
  - Factories take arguments: ``dirty_row(order_id="o-9")`` overrides just
    the fields a test cares about, so each test reads like its scenario.
  - The test suite for this repo IS the demo: ``tests/test_day_14.py``
    uses real ``@pytest.fixture`` and ``@pytest.mark.parametrize`` —
    the day's topic, running the day's own checks.

Your solution: ``dirty_row(**overrides)`` and ``fresh_batch(n=3)`` below.
Then run the tests: ``python -m pytest tests -q`` from the day-14 folder.

ANALOGY
-------
A fixture factory is a hotel turndown service: every guest (test) walks
into a freshly made room. A shared module-level dict is one unmade bed
that every guest sleeps in, in order.
"""


def dirty_row(**overrides):
    """Build one dirty order row; overrides set just the fields you care about."""
    row = {"order_id": "o-1", "amount": "1,234.56", "status": "paid"}
    row.update(overrides)
    return row


def fresh_batch(n=3):
    """Build a brand-new batch of n dirty rows — new list, new dicts, every call."""
    return [
        dirty_row(order_id=f"o-{i}", amount=str(10 * i), status="paid")
        for i in range(1, n + 1)
    ]


def upper_status(row):
    """Tiny transform under test: normalize the status field to UPPER."""
    return {**row, "status": str(row.get("status", "")).upper()}
