"""Day 38 - Problem 2: Three-valued logic — TRUE, FALSE, UNKNOWN.

Every comparison with NULL is UNKNOWN, not false: ``NULL = NULL``
is UNKNOWN, ``NOT UNKNOWN`` is UNKNOWN. But the logic is not
symmetric: ``UNKNOWN AND FALSE`` is FALSE (one FALSE decides an
AND), and ``UNKNOWN OR TRUE`` is TRUE (one TRUE decides an OR).
That asymmetry is where bugs hide — a filter that looks like a
complement is not one.
"""

from __future__ import annotations

import sqlite3


def truth_table(
    conn: sqlite3.Connection,
) -> list[tuple[str, int | None]]:
    """The eight expressions that decide the whole lesson.

    Returns (expression, result) with UNKNOWN as None: the two
    comparisons and NOT are UNKNOWN; AND with FALSE is FALSE (0);
    OR with TRUE is TRUE (1); the other two stay UNKNOWN.
    """
    rows = conn.execute(
        """
        SELECT 'NULL = NULL', NULL = NULL
        UNION ALL SELECT 'NULL <> 1', NULL <> 1
        UNION ALL SELECT 'NOT NULL', NOT NULL
        UNION ALL SELECT 'NULL AND 0', NULL AND 0
        UNION ALL SELECT 'NULL AND 1', NULL AND 1
        UNION ALL SELECT 'NULL OR 0', NULL OR 0
        UNION ALL SELECT 'NULL OR 1', NULL OR 1
        """
    ).fetchall()
    return [(expr, result) for expr, result in rows]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    for expr, result in truth_table(conn):
        print(f"{expr:16} -> {result}")
