"""Day 20 - Problem 4: the tradeoff table, executable.

Opinions about formats are cheap; bytes are not. ``shootout`` takes
the same batch of order records and serializes it three ways — JSON
(the labeled suitcase), Avro (the vacuum bag), Parquet (the shipping
container) — then reports bytes, encode/decode time, and whether the
round trip was faithful. The table this prints is the one to paste
into the design doc the next time someone says "just use JSON for
everything."
"""
import io
import json
import time

import fastavro
import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "order_id", "type": "string"},
        {"name": "region", "type": "string"},
        {"name": "qty", "type": "int"},
        {"name": "amount", "type": "double"},
    ],
}
_PARSED = fastavro.parse_schema(SCHEMA)


def make_orders(n):
    """Deterministic order records: few distinct regions, numeric facts."""
    regions = ["us-east", "eu-west", "ap-south"]
    return [
        {
            "order_id": "o-%06d" % i,
            "region": regions[i % 3],
            "qty": (i % 9) + 1,
            "amount": round(10.0 + (i * 7.13) % 990.0, 2),
        }
        for i in range(n)
    ]


def to_json(records):
    return json.dumps(records).encode("utf-8")


def to_avro(records):
    buf = io.BytesIO()
    fastavro.writer(buf, _PARSED, records)
    return buf.getvalue()


def to_parquet(records):
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(records), buf)
    return buf.getvalue()


def from_json(payload):
    return json.loads(payload)


def from_avro(payload):
    return list(fastavro.reader(io.BytesIO(payload)))


def from_parquet(payload):
    return pq.read_table(io.BytesIO(payload)).to_pylist()


def shootout(n=2000):
    """Serialize ``n`` orders three ways.

    Returns ``{format: {"bytes", "encode_s", "decode_s", "faithful"}}``.
    Size ordering is asserted in the tests; timings are reported, not
    asserted — clocks are noisy, bytes are not.
    """
    records = make_orders(n)
    codecs = (
        ("json", to_json, from_json),
        ("avro", to_avro, from_avro),
        ("parquet", to_parquet, from_parquet),
    )
    out = {}
    for name, encode, decode in codecs:
        t0 = time.perf_counter()
        payload = encode(records)
        t1 = time.perf_counter()
        back = decode(payload)
        t2 = time.perf_counter()
        out[name] = {
            "bytes": len(payload),
            "encode_s": t1 - t0,
            "decode_s": t2 - t1,
            "faithful": back == records,
        }
    return out


if __name__ == "__main__":
    table = shootout()
    print("%-8s %10s %10s %10s %s" % ("format", "bytes", "enc_s", "dec_s", "faithful"))
    for name, row in table.items():
        print(
            "%-8s %10d %10.3f %10.3f %s"
            % (name, row["bytes"], row["encode_s"], row["decode_s"], row["faithful"])
        )
