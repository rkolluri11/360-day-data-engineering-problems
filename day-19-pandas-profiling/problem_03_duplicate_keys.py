"""Day 19 - Problem 3: duplicate keys.

One duplicated order_id doubles revenue the moment a join fans it out.
``duplicate_report`` counts the duplicated key values (not just rows:
a key appearing 3 times contributes 1 distinct offender) and returns
the offending rows so the quarantine step can route them with a reason.
"""
import pandas as pd


def duplicate_report(df: pd.DataFrame, key_cols) -> dict:
    """Report duplicates on ``key_cols`` (a column name or list).

    Returns ``n_duplicate_rows`` (rows whose key repeats), ``n_duplicate_keys``
    (distinct key values that repeat), and ``offending_rows`` (the rows).
    """
    if isinstance(key_cols, str):
        key_cols = [key_cols]
    mask = df.duplicated(subset=key_cols, keep=False)
    offending = df.loc[mask]
    return {
        "n_duplicate_rows": int(mask.sum()),
        "n_duplicate_keys": int(offending.drop_duplicates(subset=key_cols).shape[0]),
        "offending_rows": offending.reset_index(drop=True),
    }


if __name__ == "__main__":
    df = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o2", "o3", "o3", "o3", "o4"],
            "amount": [10.0, 20.0, 20.0, 30.0, 30.0, 30.0, 40.0],
        }
    )
    rep = duplicate_report(df, "order_id")
    print("dup rows:", rep["n_duplicate_rows"], "| dup keys:", rep["n_duplicate_keys"])
    print(rep["offending_rows"])
