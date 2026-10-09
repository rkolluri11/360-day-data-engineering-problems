"""Problem 5 — The 10 GB log that wouldn't fit
=============================================

THE PROBLEM (beginner foothold first)
------------------------------------
You need to count ERROR lines in a 10 GB log. The rookie move:

    lines = open("huge.log").read().splitlines()  # 10 GB in RAM. OOM. 💥

The file doesn't fit in memory, so the whole "load then process"
habit has to go.

Plain words: you don't drink a river by bottling it first — you
dip the cup in as it flows past.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
The nightly 10 GB vendor log must be parsed *and validated*:
  - stream it line by line — memory stays flat no matter the size
  - parse each line with problem 1's ``parse_fields`` (quoted commas!)
  - EVERY row must have exactly ``expected_cols`` columns; a short or
    long row means upstream changed the format, and silently
    accepting it is how the wandering column (Day 5's 2 AM story)
    shifts revenue for three days
  - skip blank lines quietly, but fail LOUD on malformed rows —
    with the 1-based line number in the error

Your solution: ``stream_rows(path, expected_cols, delimiter=",")`` —
a generator that:
  - opens the file lazily and yields one parsed list per data line,
  - skips blank/whitespace-only lines,
  - raises ``RowValidationError(line_no, line, got, expected)`` the
    moment a row's column count is wrong (fail fast, at the source),
  - never holds more than one line in memory (prove it: the tests
    feed it through a generator-friendly harness, and a 1M-line
    synthetic file must parse in seconds with flat memory).

Plain words: a conveyor belt with a measuring gate — every item is
measured as it passes, and the belt STOPS on the first wrong size.

ANALOGY
-------
A toll booth, not a parking lot: cars are counted as they pass;
you never try to fit every car on the highway into the booth.

YOUR TASK
---------
Implement ``stream_rows`` and ``RowValidationError`` below. Then run:
``python -m pytest tests -q`` from the day-05 folder.
"""

from problem_01_quoted_csv_fields import parse_fields


class RowValidationError(ValueError):
    """Raised when a row's column count != expected. Carries the evidence."""

    def __init__(self, line_no, line, got, expected):
        self.line_no = line_no
        self.line = line
        self.got = got
        self.expected = expected
        super().__init__(
            f"line {line_no}: expected {expected} columns, got {got}: {line!r}"
        )


def stream_rows(path, expected_cols, delimiter=","):
    """Yield parsed rows from *path*, validating column counts.

    Generator — memory stays flat regardless of file size. Blank lines
    are skipped. Raises RowValidationError on the first malformed row.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line_no, raw in enumerate(f, start=1):
            if not raw.strip():
                continue  # blank lines are not data
            try:
                row = parse_fields(raw.rstrip("\n"), delimiter=delimiter)
            except ValueError as e:
                raise RowValidationError(line_no, raw.rstrip("\n"), -1, expected_cols) from e
            if len(row) != expected_cols:
                raise RowValidationError(line_no, raw.rstrip("\n"), len(row), expected_cols)
            yield row


if __name__ == "__main__":
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write('a,"b,c",d\n\nx,y,z\n')
        name = f.name
    print(list(stream_rows(name, 3)))
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write("a,b,c\nd,e\n")
        bad = f.name
    try:
        list(stream_rows(bad, 3))
    except RowValidationError as e:
        print("caught:", e)
    os.unlink(name)
    os.unlink(bad)
