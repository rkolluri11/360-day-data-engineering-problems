"""Problem 1 — The CSV where every value lied about its type
========================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Python's ``csv`` reader hands you *strings*. Always. So this:

    row = {"amount": "0", "refunded": "False"}

looks innocent, but watch what beginners do:

    if row["refunded"]:          # "False" is a non-empty string -> True!
        issue_refund()

``bool("False")`` is ``True`` because *any* non-empty string is
truthy. And ``int("12.5")`` doesn't round — it raises ``ValueError``.
The string doesn't care what you *meant*; the type is the truth.

Plain words: the CSV speaks only one language — text. If you don't
translate each column on purpose, Python will believe the text
version, and "False" will mean yes.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A nightly revenue job ingests a partner CSV with 2M rows. The
``amount`` column arrives as ``"$1,234.56"``, ``"1.2e3"``, ``""``,
``"N/A"``. The ``is_refund`` column arrives as ``"true"``,
``"False"``, ``"0"``, ``"no"``. The old loader did this:

    amount = float(row["amount"])        # crashes on "$1,234.56"
    refunded = bool(row["is_refund"])    # "False" -> True. Refunds for all!

One bad row raised, the whole 2M-row load aborted at 3 AM, and the
rows that *did* load before the crash had inverted refund flags.

Your solution: ``coerce_row(row, schema)`` — translate every raw
string to its declared type (``"int"``, ``"float"``, ``"bool"``,
``"str"``) and return ``(coerced, errors)``:
  - never crash the batch on one bad cell — record ``"amount:
    cannot convert 'N/A' to float"`` and keep going,
  - never use ``bool(string)`` — map explicit true/false words,
  - strip currency symbols, commas, and whitespace before numbers.

Plain words: every cell goes through customs with a passport that
says what type it claims to be. Bad passports get flagged and
logged; the rest of the line keeps moving.

ANALOGY
-------
A mailroom that receives every parcel in an identical brown box.
The label says "glassware" but the box is still a box — shake it
like books and it shatters. You open each box according to its
label, and set aside the ones whose label doesn't match what's
inside, without shutting down the whole mailroom.
"""

from __future__ import annotations

# Words the business actually sends for true/false, lowercased.
_TRUE_WORDS = {"true", "1", "yes", "y", "t"}
_FALSE_WORDS = {"false", "0", "no", "n", "f"}

# Markers partners use when a value is absent — none of these are numbers.
_MISSING_MARKERS = {"", "n/a", "na", "null", "none", "-"}


def _clean_number(text):
    """Strip whitespace, currency symbols, and thousands separators."""
    return text.strip().replace("$", "").replace(",", "")


def _to_int(text):
    cleaned = _clean_number(text)
    if cleaned.lower() in _MISSING_MARKERS:
        raise ValueError(f"missing value {text!r}")
    # int("12.5") raises on purpose — a decimal is not an integer,
    # and silently truncating money is how cents go missing.
    return int(cleaned)


def _to_float(text):
    cleaned = _clean_number(text)
    if cleaned.lower() in _MISSING_MARKERS:
        raise ValueError(f"missing value {text!r}")
    return float(cleaned)  # handles "1.2e3" and "12.50" alike


def _to_bool(text):
    word = text.strip().lower()
    if word in _TRUE_WORDS:
        return True
    if word in _FALSE_WORDS:
        return False
    # Deliberately NOT bool(text): bool("False") is True, which is
    # the exact bug that inverted every refund flag.
    raise ValueError(f"unrecognized boolean {text!r}")


_CONVERTERS = {
    "int": _to_int,
    "float": _to_float,
    "bool": _to_bool,
    "str": lambda text: text.strip(),
}


def coerce_row(row, schema):
    """Convert one raw CSV row (all strings) to typed values.

    ``row`` maps column -> raw string. ``schema`` maps column ->
    one of "int", "float", "bool", "str". Columns missing from the
    schema pass through as stripped strings.

    Returns ``(coerced, errors)``. A cell that cannot convert becomes
    ``None`` in ``coerced`` with a ``"<col>: cannot convert '<raw>'
    to <type>"`` message in ``errors`` — the row survives, the batch
    survives, and the bad cell is visible in the log.
    """
    coerced = {}
    errors = []
    for column, raw in row.items():
        target = schema.get(column, "str")
        converter = _CONVERTERS.get(target)
        if converter is None:
            raise ValueError(f"unknown target type {target!r} for {column!r}")
        # Guard: a real None (not the string "None") means the column
        # was absent upstream — flag it, don't feed it to .strip().
        if raw is None:
            coerced[column] = None
            errors.append(f"{column}: missing value (got None)")
            continue
        try:
            coerced[column] = converter(raw)
        except (ValueError, AttributeError) as exc:
            coerced[column] = None
            errors.append(f"{column}: cannot convert {raw!r} to {target} ({exc})")
    return coerced, errors


def coerce_batch(rows, schema):
    """Coerce many rows; returns (good_rows, bad_rows).

    ``good_rows`` converted with zero errors. ``bad_rows`` is a list
    of ``(original_row, errors)`` for quarantine downstream.
    """
    good_rows, bad_rows = [], []
    for row in rows:
        coerced, errors = coerce_row(row, schema)
        if errors:
            bad_rows.append((row, errors))
        else:
            good_rows.append(coerced)
    return good_rows, bad_rows


if __name__ == "__main__":
    schema = {"txn_id": "str", "amount": "float", "is_refund": "bool",
              "quantity": "int"}
    raw_rows = [
        {"txn_id": "  A-1 ", "amount": "$1,234.56", "is_refund": "False",
         "quantity": "2"},
        {"txn_id": "A-2", "amount": "1.2e3", "is_refund": "no",
         "quantity": "3"},
        {"txn_id": "A-3", "amount": "N/A", "is_refund": "maybe",
         "quantity": "12.5"},
    ]
    good, bad = coerce_batch(raw_rows, schema)
    print("good:", good)
    print("bad:")
    for original, errors in bad:
        print("  ", original["txn_id"], "->", errors)
    # Note: bool("False") would be True; _to_bool("False") is False.
