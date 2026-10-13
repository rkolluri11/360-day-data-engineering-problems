"""Day 10 tests — every solution must pass before the day is committed."""

import sys
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_config_as_record import RetryPolicy, build_retry
from problem_02_fail_at_the_door import strict_build
from problem_03_frozen_records import Record, dedup, rename, try_mutate
from problem_04_validate_at_birth import BatchConfig
from problem_05_factory_defaults import (
    SloppyStage,
    Stage,
    TaggedStage,
    shares_default,
)


# --- Problem 1: build_retry ---------------------------------------------------

def test_01_builds_from_full_mapping():
    p = build_retry({"max_attempts": 5, "backoff_s": 1.5})
    assert (p.max_attempts, p.backoff_s) == (5, 1.5)


def test_01_missing_keys_take_defaults():
    p = build_retry({})
    assert (p.max_attempts, p.backoff_s) == (3, 2.0)


def test_01_typo_key_raises_naming_it():
    with pytest.raises(TypeError) as e:
        build_retry({"max_attemps": 5})
    assert "max_attemps" in str(e.value)


def test_01_non_mapping_raises_type_error():
    with pytest.raises(TypeError):
        build_retry([("max_attempts", 3)])
    with pytest.raises(TypeError):
        build_retry(None)


# --- Problem 2: strict_build --------------------------------------------------

def test_02_builds_clean_mapping():
    @dataclass(frozen=True)
    class Sink:
        table: str = "events"
        batch_size: int = 1000

    s = strict_build(Sink, {"table": "clicks"})
    assert (s.table, s.batch_size) == ("clicks", 1000)


def test_02_lists_all_unknown_keys_sorted():
    @dataclass(frozen=True)
    class Sink:
        table: str = "events"

    with pytest.raises(TypeError) as e:
        strict_build(Sink, {"table": "x", "zeta": 1, "alpha": 2})
    msg = str(e.value)
    assert "alpha" in msg and "zeta" in msg
    assert msg.index("alpha") < msg.index("zeta")


def test_02_rejects_non_mapping():
    @dataclass(frozen=True)
    class Sink:
        table: str = "events"

    with pytest.raises(TypeError):
        strict_build(Sink, "table=events")


def test_02_empty_mapping_takes_defaults():
    @dataclass(frozen=True)
    class Sink:
        table: str = "events"
        batch_size: int = 1000

    assert strict_build(Sink, {}).batch_size == 1000


# --- Problem 3: frozen records -------------------------------------------------

def test_03_write_attempt_raises_frozen_error():
    assert try_mutate(Record(1, "raw")) is True
    with pytest.raises(FrozenInstanceError):
        Record(1, "raw").payload = "x"


def test_03_frozen_records_hash_for_dedup():
    recs = [Record(1, "a"), Record(1, "a"), Record(2, "b")]
    assert dedup(recs) == [Record(1, "a"), Record(2, "b")]


def test_03_rename_returns_new_record_original_untouched():
    r = Record(1, "raw")
    r2 = rename(r, "clean")
    assert r2.payload == "clean" and r.payload == "raw"
    assert r2 is not r


def test_03_record_usable_as_dict_key():
    seen = {Record(1, "a"): "first"}
    assert seen[Record(1, "a")] == "first"


# --- Problem 4: BatchConfig ---------------------------------------------------

def test_04_valid_config_builds_with_defaults():
    c = BatchConfig("events")
    assert (c.table, c.batch_size, c.level) == ("events", 1000, "INFO")


def test_04_bad_table_name_rejected():
    for bad in ("Events", "events-2026", "has space", "", 42):
        with pytest.raises(ValueError):
            BatchConfig(bad)


def test_04_non_positive_batch_size_rejected():
    for bad in (0, -5):
        with pytest.raises(ValueError):
            BatchConfig("events", batch_size=bad)


def test_04_unknown_level_rejected():
    with pytest.raises(ValueError):
        BatchConfig("events", level="LOUD")
    assert BatchConfig("events", level="WARN").level == "WARN"


# --- Problem 5: factory defaults ----------------------------------------------

def test_05_sloppy_stage_shares_one_list():
    a, b = SloppyStage("a"), SloppyStage("b")
    assert shares_default(a, b) is True
    a.inputs.append("leak")
    assert b.inputs == ["leak"]  # the haunting, proved


def test_05_fixed_stage_isolates_lists():
    a, b = Stage("a"), Stage("b")
    assert shares_default(a, b) is False
    a.inputs.append("ok")
    assert b.inputs == []


def test_05_dict_field_also_gets_factory():
    a, b = TaggedStage("a"), TaggedStage("b")
    a.tags["env"] = "prod"
    assert b.tags == {}
    assert a.tags is not b.tags


def test_05_explicit_inputs_still_respected():
    mine = ["x"]
    s = Stage("named", inputs=mine)
    assert s.inputs == ["x"]
    assert Stage("other").inputs == []
