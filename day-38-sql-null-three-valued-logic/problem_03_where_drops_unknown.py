"""Day 38 - Problem 3: WHERE only keeps TRUE — UNKNOWN rows vanish.

A filter drops UNKNOWN rows silently and never tells you what it
dropped. ``amount <> 12000`` returns 6 rows, not 7: the $12,000 row
and David's NULL row both go. ``NOT (amount > 10000)`` returns 4,
not 5: the NULL row is gone again. And ``amount > 10000`` itself
returns only 3 — 3 + 4 is 7, not 8. The missing row is the NULL.
"""

from __future__ import annotations

import sqlite3


def where_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Row counts for the filter and its apparent complement."""
    queries = {
        "amount_gt_10000": "SELECT COUNT(*) FROM orders WHERE amount > 10000",
        "not_amount_gt_10000": "SELECT COUNT(*) FROM orders WHERE NOT (amount > 10000)",
        "amount_ne_12000": "SELECT COUNT(*) FROM orders WHERE amount <> 12000",
        "amount_is_null": "SELECT COUNT(*) FROM orders WHERE amount IS NULL",
        "total_orders": "SELECT COUNT(*) FROM orders",
    }
    return {
        name: conn.execute(sql).fetchone()[0] for name, sql in queries.items()
    }


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print(where_counts(conn))
