"""Problem 3 — assert like a data engineer: row counts, keys, nulls
====================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``assert result == expected`` is fine for one function. Pipelines need
DATA assertions — statements about the shape of a whole batch:

  - did every row survive? (row-count invariant)
  - is the key unique after dedupe? (no double-counted orders)
  - how dirty is this column? (null-rate threshold)
  - does every row carry the contract fields? (schema check)

Plain words: these are the bouncer's checklist — headcount, ID check,
dress code — applied to the data before it enters the club (the
downstream table).

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A bare ``assert`` tells you WHAT failed, not WHICH rows. Each helper
    below raises AssertionError naming the offending rows and values, so
    the 3 AM reader knows where to look without re-running anything.
  - ``assert_unique`` must report the duplicated key VALUES and their
    row indices — "3 duplicate order_ids" is a shrug; "o-7 at rows 4, 9"
    is a fix.
  - Null-rate is a float comparison with a threshold: ``<= max_rate``
    passes, and the message prints the measured rate (0.40, not "too
    many"). Empty batches raise — asserting over zero rows is a test
    bug, not a pass.
  - ``assert_schema`` checks key PRESENCE, not truthiness: a row with
    ``{"amount": None}`` has the field (it is null, which is data);
    a row missing the key entirely broke the contract upstream.

Your solution: ``dedupe_by_key``, ``null_rate``, ``assert_unique``,
``assert_null_rate``, and ``assert_schema`` below.
Then run the tests: ``python -m pytest tests -q`` from the day-14 folder.

ANALOGY
-------
Data assertions are the pre-flight checklist: the plane does not take
off because the pilot feels good about it — it takes off because every
line on the card was read aloud and answered.
"""


def dedupe_by_key(rows, key):
    """Drop later rows whose key was already seen; keep first occurrence."""
    seen, out = set(), []
    for row in rows:
        k = row.get(key)
        if k not in seen:
            seen.add(k)
            out.append(row)
    return out


def null_rate(rows, field):
    """Fraction of rows where field is None or blank. Empty batch -> 0.0."""
    if not rows:
        return 0.0
    nulls = sum(
        1 for r in rows if r.get(field) is None or str(r.get(field)).strip() == ""
    )
    return nulls / len(rows)


def assert_unique(rows, key):
    """Raise AssertionError naming duplicate key values and their indices."""
    positions = {}
    for i, row in enumerate(rows):
        positions.setdefault(row.get(key), []).append(i)
    dupes = {k: idx for k, idx in positions.items() if len(idx) > 1}
    if dupes:
        detail = ", ".join(f"{k!r} at rows {idx}" for k, idx in dupes.items())
        raise AssertionError(f"duplicate {key}: {detail}")
    return True


def assert_null_rate(rows, field, max_rate):
    """Raise unless the null rate of field is within the allowed threshold."""
    if not rows:
        raise AssertionError("assert_null_rate: no rows to check (empty batch)")
    rate = null_rate(rows, field)
    if rate > max_rate:
        raise AssertionError(
            f"null rate of {field!r} is {rate:.2f}, above allowed {max_rate:.2f} "
            f"({int(rate * len(rows))}/{len(rows)} rows null)"
        )
    return True


def assert_schema(rows, required):
    """Raise unless every row carries every required key (presence, not truthiness)."""
    bad = {}
    for i, row in enumerate(rows):
        missing = [f for f in required if f not in row]
        if missing:
            bad[i] = missing
    if bad:
        detail = ", ".join(f"row {i} missing {m}" for i, m in bad.items())
        raise AssertionError(f"schema violation: {detail}")
    return True
