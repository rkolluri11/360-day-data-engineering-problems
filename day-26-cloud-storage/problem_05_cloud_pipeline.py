"""Problem 5 — the cloud pipeline end to end: partitions, manifest, proof.

THE PROBLEM (beginner foothold first)
------------------------------------
A daily job writes one partition per day into cloud storage. The
downstream reader needs a promise stronger than "the upload finished":
every expected date present, every file exactly the bytes that were
written, and a re-run that changes nothing. Without that promise, a
missing Tuesday is discovered by a dashboard gap, not by the pipeline.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Partition keys follow the Hive layout
    ``<base>/year=YYYY/month=MM/day=DD/data.parquet`` with zero-padded
    month and day; a bad date (month 13, day 0, non-int parts) is
    rejected before anything is written.
  - Upload is idempotent per partition: re-uploading identical bytes
    for a date returns the same manifest entry and writes nothing new;
    uploading different bytes for an already-written date raises —
    partitions are immutable, and a silent overwrite is data loss
    wearing a retry's clothes.
  - The manifest is the proof: one entry per partition with key,
    size, and MD5 checksum. ``verify_dataset`` re-reads the store and
    reports every defect as a named string — ``missing:<key>``,
    ``size_mismatch:<key>``, ``checksum_mismatch:<key>`` — and an
    empty list means healthy, not "unchecked".
  - ``missing_partitions`` names exactly which expected dates never
    made it into the manifest, so the retry can target Tuesday
    instead of re-running the whole month.

Plain words: write each day once, under a key anyone can predict,
keep a receipt with a checksum on it, and check the receipt before
you tell anyone the data is ready.
"""

import hashlib
from datetime import date


class DatasetError(ValueError):
    """Raised for a bad partition date or an immutable-partition clash."""


def partition_key(base, year, month, day):
    """Return the Hive-layout key for one daily partition.

    Raises DatasetError for non-int parts or an impossible calendar
    date; the real ``datetime.date`` check does the calendar work, so
    2026-02-29 is rejected exactly like month 13.
    """
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (year, month, day)):
        raise DatasetError("year, month, and day must be ints")
    try:
        date(year, month, day)
    except ValueError:
        raise DatasetError(
            f"invalid partition date: {year}-{month}-{day}") from None
    if not base or base.startswith("/") or base.endswith("/"):
        raise DatasetError(f"invalid dataset base: {base!r}")
    return f"{base}/year={year:04d}/month={month:02d}/day={day:02d}/data.parquet"


def _checksum(data):
    return hashlib.md5(data).hexdigest()


def upload_dataset(store, base, partitions):
    """Upload ``{date_string: bytes}`` partitions into ``store``.

    ``date_string`` is ``"YYYY-MM-DD"``. Returns the manifest: a list
    of ``{"date", "key", "size", "md5"}`` dicts sorted by date.
    Identical re-uploads are no-ops for that partition; different
    bytes for an existing partition raise DatasetError. ``store`` is a
    plain dict key -> bytes, shared with the caller.
    """
    manifest = []
    for date_string in sorted(partitions):
        try:
            year, month, day = (int(p) for p in date_string.split("-"))
        except (ValueError, AttributeError):
            raise DatasetError(
                f"invalid partition date string: {date_string!r}") from None
        key = partition_key(base, year, month, day)
        data = partitions[date_string]
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("partition data must be bytes")
        data = bytes(data)
        if key in store and store[key] != data:
            raise DatasetError(
                f"partition {date_string} already written with different bytes")
        store[key] = data
        manifest.append({"date": date_string, "key": key,
                         "size": len(data), "md5": _checksum(data)})
    return manifest


def verify_dataset(store, manifest):
    """Return a sorted list of defect strings, empty when healthy."""
    defects = []
    for entry in manifest:
        key = entry["key"]
        if key not in store:
            defects.append(f"missing:{key}")
        elif len(store[key]) != entry["size"]:
            defects.append(f"size_mismatch:{key}")
        elif _checksum(store[key]) != entry["md5"]:
            defects.append(f"checksum_mismatch:{key}")
    return sorted(defects)


def missing_partitions(expected_dates, manifest):
    """Return sorted expected dates absent from ``manifest``."""
    present = {entry["date"] for entry in manifest}
    return sorted(d for d in expected_dates if d not in present)
