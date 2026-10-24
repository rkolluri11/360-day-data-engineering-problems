"""Day 20 - Problem 5: pick the reader first, the format follows.

THE PROBLEM (beginner foothold first)
------------------------------------
Four formats, four jobs. The choice is not "which is best" —
it is "who reads this, and what must they trust":

    humans debugging      -> JSON      (readable everywhere)
    services evolving     -> Avro      (schema is the contract)
    analytics at scale    -> Parquet   (columnar scans)
    one trusted process   -> Pickle     (fast, Python-only)

``choose_format`` encodes that decision tree. The ORDER of the
checks is the lesson: safety first, then the job.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The trust check comes FIRST: untrusted source rules out
    Pickle unconditionally — no matter how convenient it is.
    Convenience never outranks the trust boundary.
  - Human debugging outranks compactness: a 3 AM incident is
    cheaper when the payload is readable with ``curl``.
  - Schema evolution outranks raw speed for anything two
    teams own: Avro's registry rejects breaking changes at
    publish time, before bad data flows.
  - Columnar scans outrank row convenience at scale: if the
    job reads 2 of 50 columns over millions of rows, Parquet
    is not an optimization — it is the architecture.
  - Pickle survives only when ALL of these hold: Python-only,
    single trusted process, never persisted across a deploy.

Your solution: ``choose_format`` is already written. The tests
walk the whole decision tree — including the traps: untrusted
+ pickle-requested still refuses pickle, and human-readable
beats compact when both are asked.

ANALOGY
-------
Choosing a format by benchmark is choosing a moving box by
weight alone. The question is not how heavy it is — it is who
opens it, and whether they have the right key.
"""


def choose_format(
    human_readable=False,
    schema_evolution=False,
    columnar_scan=False,
    python_only=False,
    trusted=True,
):
    """Return 'json', 'avro', 'parquet', or 'pickle' for the job.

    Decision order (safety first, then the job):
    1. Untrusted source -> pickle is off the table, always.
    2. Humans need to read/debug it -> json.
    3. Producers/consumers evolve over time -> avro.
    4. Bulk scans over few columns -> parquet.
    5. Python-only, trusted, in-process -> pickle.
    """
    if not trusted:
        # The trust boundary outranks everything: pickle can run code.
        if human_readable:
            return "json"
        if schema_evolution:
            return "avro"
        return "json"  # safe default: readable, no code execution
    if human_readable:
        return "json"
    if schema_evolution:
        return "avro"
    if columnar_scan:
        return "parquet"
    if python_only:
        return "pickle"
    return "json"  # the lingua franca is the safe default


if __name__ == "__main__":
    cases = [
        ("API response", dict(human_readable=True)),
        ("Kafka topic, v3 next quarter", dict(schema_evolution=True)),
        ("lake export, 2 of 50 cols", dict(columnar_scan=True)),
        ("in-process memo cache", dict(python_only=True)),
        ("uploaded file bytes", dict(trusted=False, python_only=True)),
    ]
    for name, kw in cases:
        print(f"{name:32s} -> {choose_format(**kw)}")
