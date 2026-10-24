"""Day 20 - Problem 3: Avro — the schema is the contract.

THE PROBLEM (beginner foothold first)
------------------------------------
JSON has no schema: a producer can rename a field and the
consumer finds out at 2 AM. Avro is schema-FIRST: the writer's
schema describes every record, and the reader can use a
DIFFERENT schema — as long as the two are compatible:

    schema v1: {user_id, amount}
    schema v2: {user_id, amount, nickname = None}   # added field, has default

A consumer written against v1 keeps reading v2 data. A
consumer on v2 reads old v1 data and fills ``nickname`` with
the default. That is schema evolution — services upgrading on
different schedules without breaking each other.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Compatibility has rules: you may ADD a field only with a
    default; you may REMOVE a field only if no reader needs
    it; you may never change a field's type incompatibly.
  - In production the schema lives in a SCHEMA REGISTRY, not
    next to the code — the registry rejects incompatible
    schemas at publish time, before bad data flows.
  - Avro's binary encoding is compact and fast, but
    unreadable to humans: you debug with the schema in hand,
    not with ``curl``.
  - The reader schema wins: resolution happens at READ time,
    so one topic can serve consumers on three schema versions
    at once.

Your solution: ``write_records``, ``read_records``, and
``evolve`` are already written (fastavro). The tests prove an
exact roundtrip — and that old bytes read through a newer
schema pick up the new field's default.

ANALOGY
-------
Avro is the standardized shipping crate with a printed
manifest. The warehouse (consumer) checks the manifest, not
the box — and a new line on the manifest does not break the
old forklifts.
"""
import io

import fastavro

SCHEMA_V1 = {
    "type": "record",
    "name": "Event",
    "fields": [
        {"name": "user_id", "type": "string"},
        {"name": "amount", "type": "double"},
    ],
}

SCHEMA_V2 = {
    "type": "record",
    "name": "Event",
    "fields": [
        {"name": "user_id", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "nickname", "type": ["null", "string"], "default": None},
    ],
}


def write_records(records, schema):
    """Serialize ``records`` with ``schema`` to Avro container bytes."""
    buf = io.BytesIO()
    fastavro.writer(buf, fastavro.parse_schema(schema), records)
    return buf.getvalue()


def read_records(data, writer_schema=None, reader_schema=None):
    """Read Avro container ``data`` back as a list of dicts.

    Pass ``reader_schema`` to resolve old bytes through a newer
    schema (schema evolution).
    """
    buf = io.BytesIO(data)
    kwargs = {}
    if reader_schema is not None:
        kwargs["reader_schema"] = fastavro.parse_schema(reader_schema)
    return list(fastavro.reader(buf, **kwargs))


def evolve(data_written_with_v1):
    """Read v1 bytes through the v2 reader schema (new field w/ default)."""
    return read_records(data_written_with_v1, reader_schema=SCHEMA_V2)


if __name__ == "__main__":
    records = [
        {"user_id": "u-7", "amount": 19.99},
        {"user_id": "u-8", "amount": 4.50},
    ]
    blob = write_records(records, SCHEMA_V1)
    print("v1 bytes:", len(blob))
    print("read back:", read_records(blob))
    print("evolved:", evolve(blob))
