"""Problem 4 — The loop that tried to swallow the ocean
====================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A file object is *already* a lazy iterator — ``for line in f``
reads one line at a time. But beginners do this:

    lines = f.readlines()      # loads ALL 8 GB into RAM at once
    for line in lines:
        ...

``readlines()`` builds the whole list first; the loop never gets
a chance to be lazy. Same with ``list(reader)`` on a csv reader.
The fix is boring and total: never materialize what you can
stream — loop directly over the iterator.

Plain words: drink from the pipe with a cup, don't dam the river
into a lake first and then drink from the lake.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
A settlement job replays a multi-GB transaction log,
``settlement.log``, where each line is ``CURRENCY,AMOUNT``:

    USD,12.50
    EUR,7.25

Requirements from the 2 AM incident review:
  - Running per-currency totals, but the file never fits in RAM —
    process it in fixed-size *chunks* of N lines.
  - A poison-pill line ``__POISON__`` means "upstream aborted;
    stop immediately and report partial totals" — the job must
    *break* out and say it did NOT finish cleanly.
  - Blank and malformed lines are skipped and counted, never fatal.
  - The caller must be able to tell "processed the whole file"
    from "stopped early" — this is exactly what ``for...else``
    is for: the ``else`` runs only if the loop never hit ``break``.

Your solution: ``stream_totals(lines, chunk_size=1000,
sentinel="__POISON__")`` returns a report dict:

    {"totals": {"USD": 12.5, ...}, "rows_seen": 120,
     "skipped": 3, "completed": True}

``lines`` is any iterable of strings (a real file object works —
nothing is ever ``list()``-ed). Chunks are pulled with
``itertools.islice`` so memory stays flat no matter how big the
file is.

Plain words: the crew works the conveyor in fixed-size trays,
keeps a running tally per currency on a clipboard, hits the red
stop button the moment the poison pill appears, and the shift
report says honestly whether the belt ran to the end or was
stopped early.

ANALOGY
-------
Counting votes from a seemingly endless ballot conveyor: you
tally in trays of 500, spoil unreadable ballots into a reject
pile with a count, and if someone drops a red "STOP — BOX
COMPROMISED" card on the belt, you halt and report partial
counts marked *incomplete* — you don't pretend you finished.
"""

from __future__ import annotations

from itertools import islice


def _parse_line(line):
    """Parse one "CURRENCY,AMOUNT" line -> (currency, amount) or None.

    Returns None for blank/malformed lines so the caller can
    ``continue`` past them. Never raises.
    """
    text = line.strip()
    if not text:
        return None
    parts = text.split(",")
    if len(parts) != 2:
        return None
    currency = parts[0].strip().upper()
    if not currency.isalpha():
        return None
    try:
        amount = float(parts[1].strip().replace("$", "").replace(",", ""))
    except ValueError:
        return None
    return currency, amount


def _chunks(iterator, size):
    """Yield lists of up to ``size`` items from an iterator, lazily.

    Plain words: scoop the conveyor into trays of `size` without
    ever holding more than one tray.
    """
    it = iter(iterator)
    while True:
        tray = list(islice(it, size))
        if not tray:
            return
        yield tray


def stream_totals(lines, chunk_size=1000, sentinel="__POISON__"):
    """Tally per-currency totals from a line stream, in chunks.

    - ``lines``: any iterable of strings (file objects welcome).
    - Memory stays flat: only one ``chunk_size`` tray is held.
    - ``sentinel`` line stops everything immediately (``break``);
      the report then says ``completed: False`` via ``for...else``.
    - Blank/malformed lines are skipped and counted (``continue``).

    Returns ``{"totals": {...}, "rows_seen": int, "skipped": int,
    "completed": bool}``.
    """
    totals = {}
    rows_seen = 0
    skipped = 0

    # The for...else below is the honest shift report: `else` runs
    # only when no `break` fired, i.e. the belt ran to the end.
    for tray in _chunks(lines, chunk_size):
        for line in tray:
            if line.strip() == sentinel:
                return {"totals": totals, "rows_seen": rows_seen,
                        "skipped": skipped, "completed": False}
            parsed = _parse_line(line)
            if parsed is None:
                skipped += 1
                continue
            currency, amount = parsed
            rows_seen += 1
            totals[currency] = totals.get(currency, 0.0) + amount
    else:
        # No break happened: every tray was consumed.
        return {"totals": totals, "rows_seen": rows_seen,
                "skipped": skipped, "completed": True}


def top_currency(report):
    """Currency with the highest total, or None if nothing tallied."""
    totals = report["totals"]
    if not totals:
        return None
    return max(totals, key=totals.get)


if __name__ == "__main__":
    # Simulate a file with a generator: nothing materialized.
    def fake_log():
        yield "USD,12.50\n"
        yield "EUR,7.25\n"
        yield "\n"                 # blank -> skipped
        yield "USD,notanumber\n"   # malformed -> skipped
        yield "EUR,2.75\n"
        yield "__POISON__\n"       # stop here
        yield "USD,999.00\n"       # never seen

    report = stream_totals(fake_log(), chunk_size=2)
    print(report)
    # {'totals': {'USD': 12.5, 'EUR': 10.0}, 'rows_seen': 3,
    #  'skipped': 2, 'completed': False}
    print("top:", top_currency(report))
