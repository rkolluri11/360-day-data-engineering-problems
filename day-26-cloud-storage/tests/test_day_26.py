"""Day 26 tests — cloud storage, S3/ADLS SDK patterns.

No network, no wall clock, no real cloud account: every bucket is an
in-memory model and every expiry is an integer timestamp. Stdlib only.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_object_keys import (
    KeyError_,
    ObjectStore,
    list_objects,
    validate_key,
)
from problem_02_multipart_upload import (
    MIN_PART_SIZE,
    MultipartError,
    MultipartStore,
)
from problem_03_presigned_access import PresignError, Presigner
from problem_04_tier_and_lifecycle import (
    LifecycleError,
    apply_lifecycle,
    monthly_cost,
    restore_time_hours,
    validate_rule,
)
from problem_05_cloud_pipeline import (
    DatasetError,
    missing_partitions,
    partition_key,
    upload_dataset,
    verify_dataset,
)


def _store_with_keys(*keys):
    store = ObjectStore()
    for key in keys:
        store.put(key, b"x")
    return store


# --- Problem 1: object keys ------------------------------------------------

def test_key_validation():
    assert validate_key("raw/events/2026/10/29/part-0001.parquet")
    assert not validate_key("")
    assert not validate_key("/leading/slash")
    assert not validate_key("trailing/slash/")
    assert not validate_key("a//b")
    assert not validate_key("a/./b")
    assert not validate_key("a/../b")
    assert not validate_key("back\\slash")
    assert not validate_key("a\tb")
    assert not validate_key(123)
    assert not validate_key("x" * 1025)


def test_delimiter_listing_rolls_up_prefixes():
    store = _store_with_keys(
        "raw/events/a.parquet", "raw/events/b.parquet", "raw/other/c.parquet")
    keys, prefixes, nxt = list_objects(store, prefix="raw/", delimiter="/")
    assert keys == []
    assert prefixes == ["raw/events/", "raw/other/"]
    assert nxt is None


def test_flat_listing_and_pagination():
    store = _store_with_keys("d/part-01", "d/part-02", "d/part-03")
    keys, _, nxt = list_objects(store, prefix="d/", max_keys=2)
    assert keys == ["d/part-01", "d/part-02"]
    assert nxt == "d/part-02"
    keys, _, nxt = list_objects(store, prefix="d/", max_keys=2,
                                continuation_token=nxt)
    assert keys == ["d/part-03"]
    assert nxt is None


def test_bad_pagination_token_and_max_keys():
    store = _store_with_keys("d/part-01")
    try:
        list_objects(store, prefix="d/", continuation_token="d/nope")
    except KeyError_:
        pass
    else:
        raise AssertionError("unknown token must raise")
    try:
        list_objects(store, prefix="d/", max_keys=0)
    except KeyError_:
        pass
    else:
        raise AssertionError("max_keys=0 must raise")


def test_zero_padded_sequence_sorts_numerically():
    store = _store_with_keys("d/part-10", "d/part-02")
    assert store.keys() == ["d/part-02", "d/part-10"]


# --- Problem 2: multipart upload ------------------------------------------

def _multipart():
    objects = {}
    return objects, MultipartStore(objects)


def test_multipart_happy_path_etag():
    objects, mp = _multipart()
    uid = mp.begin_upload("big/file.bin")
    big = b"a" * MIN_PART_SIZE
    mp.upload_part(uid, 1, big)
    mp.upload_part(uid, 2, b"tail")
    etag = mp.complete_upload(uid)
    expected = hashlib.md5(
        hashlib.md5(big).digest() + hashlib.md5(b"tail").digest()
    ).hexdigest() + "-2"
    assert etag == expected
    assert objects["big/file.bin"] == big + b"tail"
    assert mp.list_uploads() == []


def test_multipart_gap_and_small_middle_part_rejected():
    _, mp = _multipart()
    uid = mp.begin_upload("gapped.bin")
    mp.upload_part(uid, 1, b"a" * MIN_PART_SIZE)
    mp.upload_part(uid, 3, b"c")
    try:
        mp.complete_upload(uid)
    except MultipartError:
        pass
    else:
        raise AssertionError("gap must fail complete")
    uid2 = mp.begin_upload("small.bin")
    mp.upload_part(uid2, 1, b"tiny")
    mp.upload_part(uid2, 2, b"tail")
    try:
        mp.complete_upload(uid2)
    except MultipartError:
        pass
    else:
        raise AssertionError("small non-final part must fail complete")


def test_multipart_retry_replaces_part_and_abort_cleans_up():
    objects, mp = _multipart()
    uid = mp.begin_upload("retry.bin")
    mp.upload_part(uid, 1, b"first")
    mp.upload_part(uid, 1, b"second")  # retry replaces
    assert mp.complete_upload(uid).endswith("-1")
    assert objects["retry.bin"] == b"second"
    uid2 = mp.begin_upload("aborted.bin")
    mp.upload_part(uid2, 1, b"data")
    assert mp.list_uploads() == [(uid2, "aborted.bin")]
    mp.abort_upload(uid2)
    assert "aborted.bin" not in objects
    assert mp.list_uploads() == []
    try:
        mp.complete_upload(uid2)
    except MultipartError:
        pass
    else:
        raise AssertionError("completing an aborted upload must raise")


def test_multipart_part_number_bounds():
    _, mp = _multipart()
    uid = mp.begin_upload("bounds.bin")
    for bad in (0, 10001):
        try:
            mp.upload_part(uid, bad, b"x")
        except MultipartError:
            pass
        else:
            raise AssertionError(f"part {bad} must raise")


# --- Problem 3: presigned access ------------------------------------------

def test_presigned_happy_path_and_expiry():
    signer = Presigner("shh-secret")
    url = signer.sign("mybucket", "raw/a.parquet", "GET", 3600, now=1000)
    assert signer.validate(url, "GET", now=2000)
    assert not signer.validate(url, "GET", now=4600)  # at/after expiry
    assert not signer.validate(url, "PUT", now=2000)  # method mismatch


def test_presigned_tampering_and_wrong_secret():
    signer = Presigner("shh-secret")
    url = signer.sign("mybucket", "raw/a.parquet", "GET", 3600, now=1000)
    assert not signer.validate(url.replace("a.parquet", "b.parquet"),
                               "GET", now=2000)
    assert not signer.validate(url.replace("expires=", "expires=9"),
                               "GET", now=2000)
    other = Presigner("different-secret")
    assert not other.validate(url, "GET", now=2000)


def test_presigned_revoke_and_bad_sign_request():
    signer = Presigner("shh-secret")
    url = signer.sign("mybucket", "raw/a.parquet", "GET", 3600, now=1000)
    signer.revoke(url)
    assert not signer.validate(url, "GET", now=2000)
    try:
        signer.sign("mybucket", "raw/a.parquet", "POST", 60, now=1000)
    except PresignError:
        pass
    else:
        raise AssertionError("unsupported method must raise")
    try:
        signer.sign("mybucket", "raw/a.parquet", "GET", 0, now=1000)
    except PresignError:
        pass
    else:
        raise AssertionError("non-positive expiry must raise")


# --- Problem 4: tiers and lifecycle ----------------------------------------

_RULE = {"prefix": "raw/",
         "transitions": [(30, "Cool"), (365, "Archive")],
         "expiration_days": 2555}


def test_lifecycle_rule_validation():
    assert validate_rule(_RULE)
    assert validate_rule({"prefix": "raw/", "transitions": []})
    assert not validate_rule({"transitions": []})  # no prefix key
    assert not validate_rule({"prefix": "raw/",
                              "transitions": [(30, "Archive"),
                                              (10, "Cool")]})  # ages decrease
    assert not validate_rule({"prefix": "raw/",
                              "transitions": [(30, "Cool"), (60, "Hot")]})
    assert not validate_rule({"prefix": "raw/",
                              "transitions": [(30, "Cool")],
                              "expiration_days": 30})  # not after transition


def test_lifecycle_application_and_cost():
    assert apply_lifecycle("raw/a.parquet", 10, _RULE) == ("Hot", False)
    assert apply_lifecycle("raw/a.parquet", 30, _RULE) == ("Cool", False)
    assert apply_lifecycle("raw/a.parquet", 400, _RULE) == ("Archive", False)
    assert apply_lifecycle("raw/a.parquet", 2555, _RULE) == ("Archive", True)
    assert apply_lifecycle("serve/a.parquet", 400, _RULE) == ("Hot", False)
    assert monthly_cost(100, "Hot") == 2.0
    assert monthly_cost(100, "Archive") == 0.1
    assert restore_time_hours("Archive", "standard") == 12
    assert restore_time_hours("Archive", "bulk") == 48
    assert restore_time_hours("Cool", "standard") == 0
    try:
        restore_time_hours("Hot", "rocket")
    except LifecycleError:
        pass
    else:
        raise AssertionError("unknown retrieval speed must raise")


# --- Problem 5: cloud pipeline ---------------------------------------------

def test_partition_key_layout_and_bad_dates():
    assert partition_key("events", 2026, 10, 29) == \
        "events/year=2026/month=10/day=29/data.parquet"
    assert partition_key("events", 2026, 2, 5) == \
        "events/year=2026/month=02/day=05/data.parquet"
    for bad in ((2026, 13, 1), (2026, 2, 29), (2026, 1, 0)):
        try:
            partition_key("events", *bad)
        except DatasetError:
            pass
        else:
            raise AssertionError(f"{bad} must raise")


def test_pipeline_upload_verify_and_idempotency():
    store = {}
    parts = {"2026-10-28": b"day28", "2026-10-29": b"day29"}
    manifest = upload_dataset(store, "events", parts)
    assert [m["date"] for m in manifest] == ["2026-10-28", "2026-10-29"]
    assert verify_dataset(store, manifest) == []
    # Identical re-upload is a no-op with the same manifest entries.
    again = upload_dataset(store, "events", parts)
    assert again == manifest
    assert len(store) == 2
    # Different bytes for an existing partition raise, nothing overwritten.
    try:
        upload_dataset(store, "events", {"2026-10-29": b"changed"})
    except DatasetError:
        pass
    else:
        raise AssertionError("immutable partition overwrite must raise")
    assert store[manifest[1]["key"]] == b"day29"


def test_pipeline_verify_defects_and_missing_partitions():
    store = {}
    manifest = upload_dataset(store, "events", {"2026-10-28": b"day28"})
    assert missing_partitions(
        ["2026-10-27", "2026-10-28", "2026-10-29"], manifest) == \
        ["2026-10-27", "2026-10-29"]
    del store[manifest[0]["key"]]
    assert verify_dataset(store, manifest) == \
        [f"missing:{manifest[0]['key']}"]
    store[manifest[0]["key"]] = b"day29"  # same length, new bytes
    assert verify_dataset(store, manifest) == \
        [f"checksum_mismatch:{manifest[0]['key']}"]
    store[manifest[0]["key"]] = b"tiny"  # 4 bytes vs manifest size 5
    assert verify_dataset(store, manifest) == \
        [f"size_mismatch:{manifest[0]['key']}"]
