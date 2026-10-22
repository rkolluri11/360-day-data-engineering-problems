"""Day 19 - Problem 2: null census.

A raw count of nulls is a footnote. A null *rate* is a detector:
a 40% null rate in a "required" column means the upstream contract
changed, not that the data is dirty. ``null_rates`` reports the rate
per column; ``flag_nulls`` names the columns above a threshold so the
staging gate can fail the batch.
"""
import pandas as pd


def null_rates(df: pd.DataFrame) -> pd.Series:
    """Fraction of null values per column, 0.0 to 1.0."""
    if len(df) == 0:
        return pd.Series({col: 0.0 for col in df.columns}, dtype="float64")
    return df.isna().mean()


def flag_nulls(df: pd.DataFrame, threshold: float = 0.05) -> list:
    """Columns whose null rate is strictly above ``threshold``.

    Sorts by rate descending so the worst offender is listed first.
    """
    rates = null_rates(df)
    flagged = rates[rates > threshold].sort_values(ascending=False)
    return list(flagged.index)


if __name__ == "__main__":
    df = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4", None, None, None, None],
            "amount": [10.0, None, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
            "region": ["us", "eu", "us", "eu", "us", "eu", "us", "eu"],
        }
    )
    print(null_rates(df).round(3).to_dict())
    print("flagged @ 5%:", flag_nulls(df))
