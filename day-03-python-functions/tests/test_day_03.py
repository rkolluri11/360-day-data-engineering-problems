"""Day 3 tests — every solution must pass before the day is committed."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_keyword_only_steps import clean, enrich, run_step
from problem_02_retry_wrapper import TransientError, retry
from problem_03_sort_key_builder import sort_key
from problem_04_tenant_transform import make_transform
from problem_05_compose_pipeline import StageError, pipeline


# --- Problem 1: run_step ---------------------------------------------------

def test_01_new_config_keys_dont_break_old_steps():
    rows = [{"id": 1}, {}, {"id": 2}]
    config = {"batch_size": 2, "timeout": 30, "deadline": "2026-10-05"}
    result = run_step(clean, rows, config)  # 'deadline' is not clean's knob
    assert result["cleaned"] == [{"id": 1}, {"id": 2}]
    assert result["batches"] == 1
    assert result["retries_allowed"] == 3  # default kept


def test_01_catchall_step_sees_everything():
    rows = [{"id": 1}]
    result = run_step(enrich, rows, {"timeout": 5, "deadline": "x"})
    assert result["timeout"] == 5
    assert result["extra_knobs_seen"] == ["deadline"]


def test_01_missing_required_knob_fails_fast():
    with pytest.raises(TypeError) as exc_info:
        run_step(clean, [], {})  # batch_size is required
    assert "batch_size" in str(exc_info.value)
    assert "clean" in str(exc_info.value)


def test_01_keyword_only_survives_signature_growth():
    # The original 2 AM bug: a new positional param shifts every caller.
    def v1(rows, batch_size):
        return batch_size

    def v2(rows, *, batch_size, retries=3):  # grown safely: keyword-only
        return (batch_size, retries)

    assert run_step(v1, [], {"batch_size": 10}) == 10
    assert run_step(v2, [], {"batch_size": 10}) == (10, 3)


# --- Problem 2: retry -------------------------------------------------------

def test_02_success_first_try_calls_once_with_attempt_1():
    seen = []

    @retry(times=3, backoff=0.0, exceptions=(TransientError,))
    def fetch(page, *, attempt=1):
        seen.append((page, attempt))
        return "ok"

    assert fetch(7) == "ok"
    assert seen == [(7, 1)]


def test_02_retries_then_succeeds_with_attempt_numbers():
    attempts = []

    @retry(times=3, backoff=0.0, exceptions=(TransientError,))
    def flaky(*, attempt=1):
        attempts.append(attempt)
        if attempt < 3:
            raise TransientError("503")
        return "recovered"

    assert flaky() == "recovered"
    assert attempts == [1, 2, 3]


def test_02_unlisted_exception_propagates_immediately():
    calls = []

    @retry(times=3, backoff=0.0, exceptions=(TransientError,))
    def buggy(*, attempt=1):
        calls.append(attempt)
        raise KeyError("bad column")  # programming bug: NOT retried

    with pytest.raises(KeyError):
        buggy()
    assert calls == [1]


def test_02_gives_up_after_times_and_raises_last_error():
    calls = []

    @retry(times=3, backoff=0.0, exceptions=(TransientError,))
    def down(*, attempt=1):
        calls.append(attempt)
        raise TransientError(f"down on {attempt}")

    with pytest.raises(TransientError, match="down on 3"):
        down()
    assert calls == [1, 2, 3]


def test_02_backoff_is_exponential_and_injectable():
    sleeps = []

    @retry(times=4, backoff=2.0, exceptions=(TransientError,),
           sleep=sleeps.append)
    def down(*, attempt=1):
        raise TransientError("x")

    with pytest.raises(TransientError):
        down()
    assert sleeps == [2.0, 4.0, 8.0]  # no sleep after the final attempt


def test_02_preserves_identity_and_forwards_kwargs():
    received = []

    @retry(times=2, backoff=0.0, exceptions=(TransientError,))
    def load(table, *, limit, attempt=1):
        """Load a table page."""
        received.append((table, limit, attempt))
        return table

    assert load.__name__ == "load"
    assert load.__doc__ == "Load a table page."
    assert load("orders", limit=100) == "orders"
    assert received == [("orders", 100, 1)]  # kwargs arrived untouched


def test_02_rejects_nonsense_times():
    with pytest.raises(ValueError):
        retry(times=0)


# --- Problem 3: sort_key ----------------------------------------------------

MESSY = [
    {"ts": 169, "user": "a"},
    {"ts": "2024-01-01", "user": "b"},
    {"user": "c"},              # missing key
    {"ts": None, "user": "d"},  # explicit null
    {"ts": 42, "user": "e"},
]


def test_03_missing_and_none_sort_last_never_raise():
    users = [r["user"] for r in sorted(MESSY, key=sort_key("ts"))]
    assert users[:3] == ["e", "a", "b"]  # 42 < 169 < "2024-01-01" (numbers first)
    assert users[3:] == ["c", "d"]       # missing/None last, stable order


def test_03_mixed_types_never_raise():
    rows = [{"v": 5}, {"v": "x"}, {"v": 1.5}, {"v": "a"}, {"v": None}]
    result = [r["v"] for r in sorted(rows, key=sort_key("v"))]
    assert result == [1.5, 5, "a", "x", None]


def test_03_desc_is_per_field():
    rows = [
        {"region": "eu", "ts": 1},
        {"region": "eu", "ts": 3},
        {"region": "us", "ts": 2},
    ]
    result = [(r["region"], r["ts"])
              for r in sorted(rows, key=sort_key("region", "ts", desc=("ts",)))]
    assert result == [("eu", 3), ("eu", 1), ("us", 2)]


def test_03_desc_puts_missing_first_like_sql():
    rows = [{"ts": 1}, {"ts": None}, {"ts": 2}]
    result = [r["ts"] for r in sorted(rows, key=sort_key("ts", desc=("ts",)))]
    assert result == [None, 2, 1]


def test_03_rejects_bad_configuration():
    with pytest.raises(ValueError):
        sort_key()
    with pytest.raises(ValueError, match="unknown field"):
        sort_key("ts", desc=("nope",))


def test_03_sorts_200k_messy_rows_fast():
    import random
    rng = random.Random(7)
    rows = []
    for i in range(200_000):
        pick = rng.random()
        if pick < 0.7:
            rows.append({"ts": rng.randrange(1_000_000)})
        elif pick < 0.85:
            rows.append({"ts": str(rng.randrange(1_000_000))})
        elif pick < 0.95:
            rows.append({})
        else:
            rows.append({"ts": None})
    start = time.perf_counter()
    out = sorted(rows, key=sort_key("ts"))
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"{elapsed:.1f}s — key function too slow"
    assert len(out) == 200_000
    # Missing/None are the tail.
    assert all("ts" not in r or r["ts"] is None for r in out[-20_000:])


# --- Problem 4: make_transform ------------------------------------------------

def test_04_tenants_cannot_share_mutable_config():
    a = make_transform(rate=0.07, required_fields=["id"])
    b = make_transform(rate=0.20, required_fields=["id", "vat"])
    b.config()["required_fields"].append("sneaky")  # mutating B's snapshot...
    assert a.config()["required_fields"] == ["id"]  # ...must not touch A
    assert b.config()["required_fields"] == ["id", "vat"]


def test_04_transform_applies_rate_and_validates():
    t = make_transform(rate=0.10, required_fields=["id"])
    assert t({"id": 1, "total": 100.0}) == {
        "id": 1, "total": 100.0, "taxed_total": 110.0}
    # required-field check:
    t2 = make_transform(rate=0.10, required_fields=["id", "vat"])
    with pytest.raises(ValueError, match="vat"):
        t2({"id": 1, "total": 5.0})


def test_04_per_call_overrides_do_not_stick():
    t = make_transform(rate=0.07)
    row = {"id": 1, "total": 100.0}
    assert t(row, rate=0.50)["taxed_total"] == 150.0
    assert t(row)["taxed_total"] == 107.0  # override did not leak


def test_04_with_config_returns_new_transform():
    base = make_transform(rate=0.07)
    derived = base.with_config(rate=0.15)
    row = {"id": 1, "total": 100.0}
    assert derived(row)["taxed_total"] == 115.0
    assert base(row)["taxed_total"] == 107.0  # original untouched


def test_04_missing_rate_raises_clearly():
    t = make_transform(required_fields=[])
    with pytest.raises(KeyError, match="rate"):
        t({"id": 1})
    # ...but a per-call rate fills the gap:
    assert t({"id": 1, "total": 10.0}, rate=0.1)["taxed_total"] == 11.0


# --- Problem 5: pipeline ------------------------------------------------------

def _upper(rows, **ctx):
    return [r.upper() for r in rows]


def _exclaim(rows, **ctx):
    suffix = ctx.get("suffix", "!")
    return [r + suffix for r in rows]


def test_05_stages_run_in_order_with_shared_ctx():
    run = pipeline(_upper, ("shout", _exclaim))
    assert run(["a", "b"], suffix="?") == ["A?", "B?"]
    assert run.stages == ["_upper", "shout"]


def test_05_failure_names_stage_index_and_input_size():
    def poison(rows, **ctx):
        raise ValueError("poison row")

    run = pipeline(_upper, ("dedupe", poison), _exclaim)
    with pytest.raises(StageError) as exc_info:
        run(["a", "b", "c"], run_id="r1")
    err = exc_info.value
    assert err.stage_name == "dedupe"
    assert err.index == 1
    assert err.n_input == 3
    assert isinstance(err.__cause__, ValueError)


def test_05_nested_pipeline_does_not_double_wrap():
    inner = pipeline(("poison", lambda rows, **ctx: 1 / 0))
    outer = pipeline(("inner", inner))
    with pytest.raises(StageError) as exc_info:
        outer([1, 2])
    assert exc_info.value.stage_name == "poison"  # inner attribution kept


def test_05_empty_pipeline_returns_input_unchanged():
    run = pipeline()
    data = [1, 2, 3]
    assert run(data) is data
    assert run.stages == []


def test_05_million_rows_through_three_stages_is_fast():
    run = pipeline(
        lambda rows, **ctx: [r + 1 for r in rows],
        lambda rows, **ctx: [r * 2 for r in rows],
        lambda rows, **ctx: [r - 1 for r in rows],
    )
    data = list(range(1_000_000))
    start = time.perf_counter()
    out = run(data)
    elapsed = time.perf_counter() - start
    assert elapsed < 15.0, f"{elapsed:.1f}s — pipeline overhead too high"
    assert out[0] == 1 and out[-1] == 1_999_999
