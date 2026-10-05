"""Day 1 tests — every solution must pass before the day is committed."""

import csv
import random
import sys
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_streaming_sum import total_amount
from problem_02_mutable_default import retry_with_cache
from problem_03_closure_capture import build_stage_callbacks
from problem_04_identity_vs_equality import dedupe
from problem_05_chunked_groupby import stream_groupby_sum

N_ROWS = 200_000  # big enough to catch the materialize-everything bug


def _write_amount_csv(path: Path, n: int = N_ROWS) -> float:
    expected = 0.0
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["amount"])
        for i in range(n):
            value = round((i * 0.37) % 100, 2)
            expected += value
            writer.writerow([value])
    return expected


def test_01_streaming_sum_correct(tmp_path):
    csv_path = tmp_path / "amounts.csv"
    expected = _write_amount_csv(csv_path)
    assert total_amount(str(csv_path)) == pytest.approx(expected)


def test_01_streaming_sum_constant_memory(tmp_path):
    """Peak memory must stay small: a list-materializing solution fails this."""
    csv_path = tmp_path / "big.csv"
    _write_amount_csv(csv_path)
    tracemalloc.start()
    try:
        total_amount(str(csv_path))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2 * 1024 * 1024, f"peak {peak/1e6:.1f} MB — not streaming"


def test_02_caches_are_isolated():
    @retry_with_cache()
    def fetch_orders():
        return ["order-1"]

    calls = {"n": 0}

    @retry_with_cache()
    def fetch_customers():
        calls["n"] += 1
        if calls["n"] == 1:
            return ["customer-1"]
        raise RuntimeError("flaky API")

    assert fetch_orders() == ["order-1"]
    assert fetch_customers() == ["customer-1"]  # first call caches
    # Second call raises, but must retry from ITS OWN cache — not orders'.
    assert fetch_customers() == ["customer-1"]
    # Orders' cache must be untouched by customers' failures.
    assert fetch_orders() == ["order-1"]


def test_03_each_callback_remembers_its_stage():
    stages = ["extract", "transform", "load"]
    callbacks = build_stage_callbacks(stages)
    assert [cb() for cb in callbacks] == [f"stage={s}" for s in stages]


def test_04_dedupe_by_value_not_identity():
    # Fresh runtime strings — never interned, like names parsed from a file.
    items = ["".join(list(s)) for s in ["dev", "staging", "dev", "prod", "staging"]]
    assert dedupe(items) == ["dev", "staging", "prod"]


def test_04_dedupe_is_linear_and_stable():
    items = [f"env-{i % 50}" for i in range(10_000)]
    result = dedupe(items)
    assert result == [f"env-{i}" for i in range(50)]


def test_05_chunked_groupby_correct(tmp_path):
    rng = random.Random(42)
    cats = [f"cat-{i}" for i in range(300)]
    csv_path = tmp_path / "sales.csv"
    expected: dict[str, float] = {}
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["category", "amount"])
        for _ in range(50_000):
            cat = rng.choice(cats)
            amount = round(rng.uniform(0, 1000), 2)
            expected[cat] = expected.get(cat, 0.0) + amount
            writer.writerow([cat, amount])
    got = stream_groupby_sum(str(csv_path), chunk_rows=2_000)
    assert set(got) == set(expected)
    for cat in expected:
        assert got[cat] == pytest.approx(expected[cat])


def test_05_chunked_groupby_memory_budget(tmp_path):
    csv_path = tmp_path / "sales.csv"
    rng = random.Random(7)
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["category", "amount"])
        for _ in range(50_000):
            writer.writerow([f"cat-{rng.randint(0, 299)}", round(rng.uniform(0, 1000), 2)])
    tracemalloc.start()
    try:
        stream_groupby_sum(str(csv_path), chunk_rows=2_000)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 5 * 1024 * 1024, f"peak {peak/1e6:.1f} MB exceeds 5 MB budget"
