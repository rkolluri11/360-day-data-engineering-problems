"""Day 39, problem 1: text sorts like text.

Scores are stored as TEXT. ORDER BY score_text DESC compares characters,
not numbers: '9' beats '2', '1' and '0', so the top "score" is 9.
CAST the value to INTEGER first, then sort — the real top score is 100.
"""

from __future__ import annotations

import sqlite3


def text_order(conn: sqlite3.Connection) -> list[str]:
    """Names ordered by the TEXT score, highest first."""
    rows = conn.execute(
        "SELECT name FROM scores ORDER BY score_text DESC"
    ).fetchall()
    return [r[0] for r in rows]


def cast_order(conn: sqlite3.Connection) -> list[str]:
    """Names ordered by the score as a number, highest first."""
    rows = conn.execute(
        "SELECT name FROM scores ORDER BY CAST(score_text AS INTEGER) DESC"
    ).fetchall()
    return [r[0] for r in rows]


def text_top_score(conn: sqlite3.Connection) -> str:
    """The top score if you sort the TEXT column as-is."""
    return text_order(conn)[0]


def cast_top_score(conn: sqlite3.Connection) -> str:
    """The top score once the values are CAST to INTEGER."""
    return cast_order(conn)[0]
