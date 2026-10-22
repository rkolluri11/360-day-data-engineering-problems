"""Day 19 tests: pandas for data validation and profiling."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_triage import triage
from problem_02_null_census import null_rates, flag_nulls
from problem_03_duplicate_keys import duplicate_report
from problem_04_outlier_fences import iqr_fences, find_outliers
from problem_05_schema_gate import validate_schema, profile_report


def make_frame():
    return pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o2", "o3", None],
            "amount": [10.0, 20.0, 20.0, 999999.0, 40.0],
            "region": ["us", "eu", "us", "eu", "us"],
        }
    )


# --- Problem 1: triage ---
def test_triage_shape_and_dtypes():
    df = make_frame()
    t = triage(df)
    assert t["n_rows"] == 5 and t["n_cols"] == 3
    assert t["dtypes"]["amount"] == "float64"
    assert t["dtypes"]["order_id"] == "object"


def test_triage_non_null_counts():
    t = triage(make_frame())
    assert t["non_null_counts"]["order_id"] == 4  # one None
    assert t["non_null_counts"]["amount"] == 5
    assert t["memory_bytes"] > 0


# --- Problem 2: null census ---
def test_null_rates_fractions():
    rates = null_rates(make_frame())
    assert rates["order_id"] == pytest.approx(0.2)
    assert rates["amount"] == 0.0


def test_flag_nulls_threshold():
    df = make_frame()
    assert flag_nulls(df, threshold=0.1) == ["order_id"]
    assert flag_nulls(df, threshold=0.5) == []


def test_null_rates_empty_frame():
    rates = null_rates(pd.DataFrame({"a": [], "b": []}))
    assert rates["a"] == 0.0 and rates["b"] == 0.0


# --- Problem 3: duplicate keys ---
def test_duplicate_report_counts():
    rep = duplicate_report(make_frame(), "order_id")
    assert rep["n_duplicate_rows"] == 2  # the two o2 rows
    assert rep["n_duplicate_keys"] == 1
    assert set(rep["offending_rows"]["order_id"]) == {"o2"}


def test_duplicate_report_clean():
    df = pd.DataFrame({"k": ["a", "b"], "v": [1, 2]})
    rep = duplicate_report(df, "k")
    assert rep["n_duplicate_rows"] == 0 and rep["n_duplicate_keys"] == 0


def test_duplicate_report_multi_column_key():
    df = pd.DataFrame({"a": [1, 1, 1], "b": [2, 2, 3]})
    rep = duplicate_report(df, ["a", "b"])
    assert rep["n_duplicate_rows"] == 2 and rep["n_duplicate_keys"] == 1


# --- Problem 4: outlier fences ---
def test_iqr_fences_sane():
    s = pd.Series([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 100.0])
    lo, hi = iqr_fences(s)
    assert lo < 1.0 and hi < 100.0  # the spike is outside


def test_find_outliers_catches_sentinels():
    df = make_frame()
    out = find_outliers(df, "amount")
    assert 999999.0 in out["amount"].values
    assert len(out) == 1  # the only fence-breaker


def test_find_outliers_ignores_nulls():
    df = pd.DataFrame({"x": [1.0, 2.0, None, 3.0, 1e9]})
    out = find_outliers(df, "x")
    assert out["x"].isna().sum() == 0


# --- Problem 5: schema gate ---
def test_validate_schema_passes():
    df = make_frame()
    validate_schema(df, {"order_id": "object", "amount": "float64"})


def test_validate_schema_catches_dtype_drift():
    df = make_frame()
    df["amount"] = df["amount"].astype(str)  # "N/A" crept in upstream
    with pytest.raises(ValueError, match="dtype drift"):
        validate_schema(df, {"amount": "float64"})


def test_validate_schema_catches_missing_column():
    df = make_frame().drop(columns=["region"])
    with pytest.raises(ValueError, match="missing column"):
        validate_schema(df, {"region": "object"})


def test_profile_report_shape():
    rep = profile_report(make_frame(), key_cols="order_id")
    assert set(rep.index) >= {"order_id", "amount", "region"}
    assert rep.loc["order_id", "null_rate"] == pytest.approx(0.2)
    assert rep.loc["amount", "n_outliers"] == 1
    assert rep.loc["region", "n_outliers"] == 0
