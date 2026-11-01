"""Problem 2 — rolling aggregates over a fixed window.

THE PROBLEM (beginner foothold first)
------------------------------------
A pipeline counts events per minute and wants the busiest 5-minute
stretch, or a moving average to smooth a spiky series. Recomputing
each window from scratch costs O(n*k) — fine for a demo, fatal for a
day of minute buckets.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Both answers come from ONE pass that slides the window: add the
    entering value, subtract the leaving one. O(n) time, O(1) extra
    space beyond the output.
  - A window size of 0, negative, or larger than the series is a
    caller bug, not an empty result: it raises ``ValueError``.
  - Moving averages are floats, and the window sum is exact: the
    average of a window is ``window_sum / k``, never a running float
    that accumulates rounding error window after window.
  - An empty series raises too — there is no window to report.

Plain words: never re-add a window you already added; just swap the
value leaving for the value entering.
"""

from typing import List, Sequence


def _validate(values: Sequence[float], k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool):
        raise ValueError("k must be an integer")
    if k < 1:
        raise ValueError("k must be at least 1")
    if len(values) == 0:
        raise ValueError("values must not be empty")
    if k > len(values):
        raise ValueError("k must not exceed len(values)")


def sliding_window_max_sum(values: Sequence[float], k: int) -> float:
    """Return the largest sum of any contiguous window of ``k`` values."""
    _validate(values, k)
    window_sum = sum(values[:k])
    best = window_sum
    for i in range(k, len(values)):
        window_sum += values[i] - values[i - k]
        if window_sum > best:
            best = window_sum
    return best


def moving_averages(values: Sequence[float], k: int) -> List[float]:
    """Return the average of every contiguous window of ``k`` values,
    in order. Each average is computed from that window's exact sum.
    """
    _validate(values, k)
    result = []
    window_sum = sum(values[:k])
    result.append(window_sum / k)
    for i in range(k, len(values)):
        window_sum += values[i] - values[i - k]
        result.append(window_sum / k)
    return result
