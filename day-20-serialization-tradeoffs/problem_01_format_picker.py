"""Day 20 - Problem 1: the boundary decision.

Beginner foothold: serialization is packing data for a trip across a
boundary — a network call, a queue, a file on disk. JSON is a clear,
labeled suitcase: anyone can open it, but it's bulky. Avro is a vacuum
bag with an instruction manual: compact, and the manual tells the
future reader what's inside. Parquet is a shipping container packed by
item type — all the shirts together — so unpacking one kind of thing
is fast. Pickle is a jack-in-the-box wired to the lock: opening a
stranger's box runs their surprise.

``choose_format`` encodes the decision table. You pick by boundary,
never by habit — and Pickle never appears on the table, because every
boundary is crossed by someone you don't fully control.
"""

# boundary -> (format, rationale)
DECISIONS = {
    "api": (
        "json",
        "public REST: universal, human-readable, debuggable in a browser",
    ),
    "event-stream": (
        "avro",
        "Kafka/Event Hubs: compact rows, schema registry, safe evolution",
    ),
    "lake": (
        "parquet",
        "analytical landing: columnar, compressed, predicate pushdown",
    ),
    "debug": (
        "json",
        "humans read it: logs, samples, incident triage",
    ),
    "cache": (
        "json",
        "shared cache: language-neutral; pickle would couple every reader to Python",
    ),
}


def choose_format(boundary: str) -> tuple:
    """Return ``(format, rationale)`` for a pipeline boundary.

    ``boundary`` is one of "api", "event-stream", "lake", "debug",
    "cache". Anything else raises ``ValueError`` — an unknown boundary
    is exactly where teams reach for pickle out of habit, so the
    function refuses to guess.
    """
    try:
        return DECISIONS[boundary]
    except KeyError:
        raise ValueError(
            "unknown boundary %r; known: %s" % (boundary, sorted(DECISIONS))
        ) from None


if __name__ == "__main__":
    for boundary in ("api", "event-stream", "lake", "debug", "cache"):
        fmt, why = choose_format(boundary)
        print("%-13s -> %-8s %s" % (boundary, fmt, why))
