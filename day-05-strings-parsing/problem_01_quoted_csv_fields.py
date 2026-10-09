"""Problem 1 — The field that ate the delimiter
================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A CSV line looks simple:

    name,address,city

``line.split(",")`` gives ``["name", "address", "city"]``. Done — until
an address contains a comma:

    Alice,"42 Main St, Apt 3",Springfield

Naive ``split(",")`` returns FOUR fields, and every column downstream
shifts. Your revenue column is now reading cities.

Plain words: the delimiter is doing double duty — separating fields
*and* sitting inside them. Quotes are the escape hatch: everything
between a pair of quotes is one field, commas included.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
Vendor files don't follow the spec. You will meet, in the same file:
  - quoted fields with embedded commas: ``"42 Main St, Apt 3"``
  - quoted fields with escaped quotes (two double-quotes become one)
  - unbalanced quotes (a typo upstream): ``name,addr"ess,city``
  - padding whitespace: ``"  ORD-42  " , 19.99``

Your solution: ``parse_fields(line, delimiter=",")`` — a small,
dependency-free parser that:
  - respects double-quoted sections (commas inside quotes don't split),
  - unescapes doubled quotes (``""`` → ``"``),
  - strips surrounding whitespace from every field,
  - raises ``ValueError`` on an unbalanced quote instead of silently
    producing shifted columns (fail fast — the 2 AM wandering column
    must never happen quietly).

Plain words: read the line like a bouncer with a guest list — if the
quotes don't pair up, nobody gets in and you hear about it now.

ANALOGY
-------
Punctuation in a contract: commas separate clauses, but a comma inside
quotation marks belongs to the quote. Misread one and the meaning —
or the money — moves.

YOUR TASK
---------
Implement ``parse_fields`` below. Then run the tests:
``python -m pytest tests -q`` from the day-05 folder.
"""


def parse_fields(line, delimiter=","):
    """Split *line* on *delimiter*, respecting double-quoted sections.

    - Commas inside double quotes do not split.
    - Doubled quotes ("") inside a quoted section become one quote.
    - Surrounding whitespace is stripped from every field.
    - Raises ValueError if a quote is left unbalanced.
    """
    fields = []
    buf = []
    in_quotes = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == '"':
            if in_quotes and i + 1 < n and line[i + 1] == '"':
                buf.append('"')  # escaped quote
                i += 2
                continue
            in_quotes = not in_quotes
            i += 1
            continue
        if ch == delimiter and not in_quotes:
            fields.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if in_quotes:
        raise ValueError(f"unbalanced quote in line: {line!r}")
    fields.append("".join(buf).strip())
    return fields


if __name__ == "__main__":
    print(parse_fields('Alice,"42 Main St, Apt 3",Springfield'))
    print(parse_fields('"say ""hi""",42'))
    try:
        parse_fields('name,addr"ess,city')
    except ValueError as e:
        print("caught:", e)
