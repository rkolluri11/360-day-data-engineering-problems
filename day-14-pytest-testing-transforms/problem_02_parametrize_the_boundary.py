"""Problem 2 — parametrize the boundary: one test, every edge
============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
``parse_amount`` must handle the zoo of real-world money strings:
``"1,234.56"``, ``"$12.50"``, ``"(45.00)"`` (accounting negative),
``"1e3"``, blanks, and garbage. Writing one test function per case is
ten copy-pasted functions. ``@pytest.mark.parametrize`` runs ONE test
function over a whole table of inputs:

    @pytest.mark.parametrize("raw,expected", [
        ("1,234.56", 1234.56),
        ("$12.50",   12.50),
        ("(45.00)",  -45.00),
    ])
    def test_parse_amount(raw, expected):
        assert parse_amount(raw) == expected

Plain words: parametrize is a crash-test rig — same dummy, same wall,
but you slam it at every speed without rebuilding the car.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The boundary is where money parsing dies: ``None`` vs ``""`` vs
    ``"   "`` (all mean "no amount", not zero — zero is a real amount),
    thousands separators, currency symbols, accounting parentheses,
    scientific notation, and strings that only LOOK numeric
    (``"12.34.56"`` must raise, not silently become 12.34).
  - Absence (None) and invalid ("abc") are DIFFERENT failures: None
    routes to quarantine as missing data; "abc" raises ValueError so the
    caller can label the row (see problem 4).
  - Parametrize the rejections too: a second table of inputs, each
    asserted with ``pytest.raises(ValueError)``.

Your solution: ``parse_amount(raw)`` below handles the full table.
Then run the tests: ``python -m pytest tests -q`` from the day-14 folder.

ANALOGY
-------
Parametrized edge cases are a bouncer checking IDs: the same three
questions (valid? blank? fake?) asked of every person in line — nobody
gets waved through because the line was long.
"""


def parse_amount(raw):
    """Parse a money string to float.

    None / blank -> None (absent, not zero). Strips "$", commas,
    whitespace; "(45.00)" -> -45.0 (accounting negative); "1e3" works.
    Anything else numeric-looking-but-wrong raises ValueError.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"bad amount: {raw!r}")
    return -value if negative else value
