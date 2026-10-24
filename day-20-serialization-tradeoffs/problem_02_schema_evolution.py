"""Day 20 - Problem 2: the contract that survives deploys.

The hard problem: producers and consumers deploy on different days.
With JSON, the schema lives in everyone's head — rename a field and
the reader silently gets ``None``. With Avro, the writer's schema
travels inside the payload, and the reader's schema declares what it
expects; Avro resolves the difference. Adding a field WITH a default
is safe: old bytes read fine under the new schema. Adding one WITHOUT
a default breaks every old payload — a deploy-time landmine you can
detect in a test instead of at 2 AM.
"""
import io

import fastavro

try:  # fastavro >= 1.10 exposes it here...
    from fastavro.schema import SchemaResolutionError
except ImportError:  # ...older/newer builds keep it in _read_common
    from fastavro._read_common import SchemaResolutionError

SCHEMA_V1 = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "order_id", "type": "string"},
        {"name": "amount", "type": "double"},
    ],
}

# v2: adds "currency" WITH a default -> old data still readable.
SCHEMA_V2_ADD_WITH_DEFAULT = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "order_id", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"},
    ],
}

# v2-broken: adds "region" WITHOUT a default -> old data unreadable.
SCHEMA_V2_ADD_NO_DEFAULT = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "order_id", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "region", "type": "string"},
    ],
}

SAMPLE = [
    {"order_id": "o-1", "amount": 19.99},
    {"order_id": "o-2", "amount": 5.0},
]


def write_avro(records, schema):
    """Serialize records; the writer schema travels in the file header."""
    buf = io.BytesIO()
    fastavro.writer(buf, fastavro.parse_schema(schema), records)
    return buf.getvalue()


def read_avro(payload, reader_schema=None):
    """Deserialize. When ``reader_schema`` differs from the writer's,
    Avro resolves the evolution — defaults fill in, incompatibilities
    raise ``SchemaResolutionError``."""
    buf = io.BytesIO(payload)
    kwargs = {}
    if reader_schema is not None:
        kwargs["reader_schema"] = fastavro.parse_schema(reader_schema)
    return list(fastavro.reader(buf, **kwargs))


def is_safe_evolution(writer_schema, reader_schema, sample):
    """True when data written with ``writer_schema`` reads cleanly
    under ``reader_schema``. Run this in CI before the deploy, not
    after the page."""
    try:
        read_avro(write_avro(sample, writer_schema), reader_schema)
        return True
    except SchemaResolutionError:
        return False


if __name__ == "__main__":
    payload = write_avro(SAMPLE, SCHEMA_V1)
    print("v1 bytes:", len(payload))
    print("read as v2 (default):", read_avro(payload, SCHEMA_V2_ADD_WITH_DEFAULT))
    print("safe evolution:", is_safe_evolution(SCHEMA_V1, SCHEMA_V2_ADD_WITH_DEFAULT, SAMPLE))
    print("safe evolution (no default):", is_safe_evolution(SCHEMA_V1, SCHEMA_V2_ADD_NO_DEFAULT, SAMPLE))
