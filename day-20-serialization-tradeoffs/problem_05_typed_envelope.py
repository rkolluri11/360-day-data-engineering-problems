"""Day 20 - Problem 5: your types must survive the trip.

The hardest realistic version: JSON has six types; your domain has
dozens. Naive ``json.dumps`` can't even carry money — ``Decimal``
raises ``TypeError`` — and with ``default=str`` a datetime silently
comes back as a string, so the downstream service parses "2026-10-23"
three different ways. Avro solves this natively with logical types;
when the boundary must stay JSON, the honest fix is a typed envelope:
the schema travels with the payload, values ride in a lossless text
encoding, and the reader restores exact Python types — or rejects the
payload when the contract drifts.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal

SCHEMA = {
    "order_id": "string",
    "amount": "decimal",       # money: exact, never float
    "qty": "int",
    "placed_at": "timestamp",  # timezone-aware datetime
}

ENVELOPE_VERSION = "typed-json/1"


def naive_dumps(record):
    """What most services do first: plain json.dumps.

    Raises TypeError on Decimal — money can't even board the truck.
    """
    return json.dumps(record)


def encode_typed(record, schema=SCHEMA):
    """Serialize with an explicit type contract.

    Decimals ride as exact strings, timestamps as ISO strings; the
    envelope carries a version and the schema so the reader can verify
    the contract before trusting the bytes.
    """
    body = {}
    for field, kind in schema.items():
        value = record[field]
        if kind == "decimal":
            body[field] = str(value)
        elif kind == "timestamp":
            body[field] = value.isoformat()
        else:
            body[field] = value
    envelope = {"v": ENVELOPE_VERSION, "schema": schema, "body": body}
    return json.dumps(envelope).encode("utf-8")


def decode_typed(payload, schema=SCHEMA):
    """Restore exact Python types per the schema.

    Raises ``ValueError`` on version mismatch or schema drift — a
    contract violation fails here, loudly, instead of corrupting the
    warehouse quietly.
    """
    env = json.loads(payload)
    if env.get("v") != ENVELOPE_VERSION:
        raise ValueError("unsupported envelope version: %r" % (env.get("v"),))
    if env.get("schema") != schema:
        raise ValueError("schema drift: payload contract != reader contract")
    out = {}
    for field, kind in schema.items():
        raw = env["body"][field]
        if kind == "decimal":
            out[field] = Decimal(raw)
        elif kind == "timestamp":
            out[field] = datetime.fromisoformat(raw)
        else:
            out[field] = raw
    return out


if __name__ == "__main__":
    order = {
        "order_id": "o-42",
        "amount": Decimal("19.99"),
        "qty": 3,
        "placed_at": datetime(2026, 10, 23, 19, 30, tzinfo=timezone.utc),
    }
    try:
        naive_dumps(order)
    except TypeError as exc:
        print("naive json:", exc)
    back = decode_typed(encode_typed(order))
    print("typed envelope round trip:", back)
    print("types:", {k: type(v).__name__ for k, v in back.items()})
