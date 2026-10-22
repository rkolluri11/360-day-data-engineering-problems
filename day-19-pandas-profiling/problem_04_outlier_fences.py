"""Day 19 - Problem 4: outlier fences.

An amount of -999 or 9,999,999 is usually a placeholder, not a sale.
Tukey's IQR fences (Q1 - 1.5*IQR, Q3 + 1.5*IQR) draw the line between
"big but real" and "probably a sentinel value someone forgot to clean".
``find_outliers`` returns the rows outside the fences for quarantine.
"""
import pandas as pd


def iqr_fences(s: pd.Series, k: float = 1.5) -> tuple:
    """Return (lower, upper) Tukey fences for ``s``, ignoring nulls."""
    s = s.dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return (float(q1 - k * iqr), float(q3 + k * iqr))


def find_outliers(df: pd.DataFrame, col: str, k: float = 1.5) -> pd.DataFrame:
    """Rows whose ``col`` value falls outside the IQR fences."""
    lower, upper = iqr_fences(df[col], k)
    mask = (df[col] < lower) | (df[col] > upper)
    return df.loc[mask & df[col].notna()].reset_index(drop=True)


if __name__ == "__main__":
    df = pd.DataFrame(
        {"amount": [48.0, 52.0, 49.0, 51.0, 50.0, 47.0, 53.0, -999.0, 9999999.0]}
    )
    print("fences:", iqr_fences(df["amount"]))
    print(find_outliers(df, "amount"))
