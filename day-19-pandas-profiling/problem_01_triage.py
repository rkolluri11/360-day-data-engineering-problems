"""Day 19 - Problem 1: the 10-second triage.

Before a single transform runs, you want three facts about any landing
frame: how big is it, what does pandas think each column is, and how
much memory it costs. ``triage`` returns exactly that as a plain dict
so the staging step can log it for every batch.
"""
import pandas as pd


def triage(df: pd.DataFrame) -> dict:
    """Return a one-dict health summary of ``df``.

    Keys: ``n_rows``, ``n_cols``, ``dtypes`` (name -> dtype string),
    ``non_null_counts`` (name -> int), ``memory_bytes``.
    """
    return {
        "n_rows": len(df),
        "n_cols": df.shape[1],
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "non_null_counts": {col: int(df[col].notna().sum()) for col in df.columns},
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
    }


if __name__ == "__main__":
    import numpy as np

    rng = np.random.default_rng(19)
    df = pd.DataFrame(
        {
            "user_id": [f"u-{i}" for i in range(1000)],
            "amount": rng.normal(50, 10, 1000),
            "event_date": pd.to_datetime("2026-10-22") + pd.to_timedelta(rng.integers(0, 7, 1000), unit="D"),
        }
    )
    df.loc[rng.choice(1000, 30, replace=False), "amount"] = None
    for k, v in triage(df).items():
        print(f"{k}: {v}")
