"""Day 19 - Problem 5: the schema gate.

The silent killer is not a dirty row - it is a column that changed type
overnight ("amount" arrives as text because one row said "N/A") or a
column that vanished. ``validate_schema`` fails fast at the gate with
a message naming exactly what drifted. ``profile_report`` assembles the
whole vital-signs sheet - one row per column - so staging can diff it
night to night.
"""
import pandas as pd


def validate_schema(df: pd.DataFrame, expected: dict) -> None:
    """Assert ``df`` matches ``expected`` {column: dtype-name}.

    Raises ValueError listing missing columns and dtype mismatches.
    Extra columns in ``df`` are allowed - upstream can add, not remove.
    """
    problems = []
    for col, want in expected.items():
        if col not in df.columns:
            problems.append(f"missing column: {col}")
        elif str(df[col].dtype) != want:
            problems.append(
                f"dtype drift: {col} is {df[col].dtype}, expected {want}"
            )
    if problems:
        raise ValueError("schema gate failed - " + "; ".join(problems))


def profile_report(df: pd.DataFrame, key_cols=None) -> pd.DataFrame:
    """One-row-per-column vital-signs sheet for the landing frame."""
    from problem_02_null_census import null_rates
    from problem_04_outlier_fences import iqr_fences

    rates = null_rates(df)
    rows = []
    for col in df.columns:
        row = {
            "column": col,
            "dtype": str(df[col].dtype),
            "n_rows": len(df),
            "null_rate": round(float(rates[col]), 4),
            "n_unique": int(df[col].nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any():
            lo, hi = iqr_fences(df[col])
            row["n_outliers"] = int(
                ((df[col] < lo) | (df[col] > hi)).sum()
            )
        else:
            row["n_outliers"] = 0
        rows.append(row)
    report = pd.DataFrame(rows).set_index("column")
    if key_cols:
        from problem_03_duplicate_keys import duplicate_report

        rep = duplicate_report(df, key_cols)
        report.loc["_dup_key_rows", "n_outliers"] = rep["n_duplicate_rows"]
    return report


if __name__ == "__main__":
    df = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "amount": [10.0, 20.0, 999999.0, 40.0],
            "region": ["us", "eu", None, "eu"],
        }
    )
    validate_schema(df, {"order_id": "object", "amount": "float64"})
    print(profile_report(df, key_cols="order_id"))
    try:
        validate_schema(df, {"order_id": "object", "amount": "int64"})
    except ValueError as e:
        print("gate caught it:", e)
