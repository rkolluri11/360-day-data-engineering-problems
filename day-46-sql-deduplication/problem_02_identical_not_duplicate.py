"""Day 46, problem 2: the identical row that is NOT a duplicate.

Frank Lopez bought $5,000 of product on 2026-02-02 — online AND
in store. Two real purchases, one identical-looking row (same
customer, same amount, same date).

- UNION ALL over online_orders + store_orders: 8 rows, $86,000.
- UNION over the same two tables: 7 rows, $81,000 — $5,000 of
  real sales vanishes, and the total now coincidentally equals
  the orders table's $81,000, which makes the error easy to miss.
- Dedup on values only when you have no key. When a key exists
  (order_id, channel, source), dedup on the key — values can
  coincide, keys should not.
"""

from __future__ import annotations

import sqlite3

_COMBINED = (
    "SELECT customer, amount, order_date FROM online_orders "
    "UNION ALL SELECT customer, amount, order_date FROM store_orders"
)


def combined_all(conn: sqlite3.Connection) -> list[tuple]:
    """All 8 channel rows, duplicates kept."""
    rows = conn.execute(
        f"SELECT * FROM ({_COMBINED}) ORDER BY customer, order_date"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def combined_all_total(conn: sqlite3.Connection) -> tuple[int, int]:
    """(row count, total) with UNION ALL: (8, 86000)."""
    return conn.execute(
        f"SELECT COUNT(*), SUM(amount) FROM ({_COMBINED})"
    ).fetchone()


def combined_distinct(conn: sqlite3.Connection) -> list[tuple]:
    """7 rows after UNION dedups on values alone."""
    rows = conn.execute(
        "SELECT customer, amount, order_date FROM online_orders "
        "UNION SELECT customer, amount, order_date FROM store_orders "
        "ORDER BY customer, order_date"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def combined_distinct_total(conn: sqlite3.Connection) -> tuple[int, int]:
    """(row count, total) with UNION: (7, 81000)."""
    return conn.execute(
        "SELECT COUNT(*), SUM(amount) FROM ("
        "SELECT customer, amount, order_date FROM online_orders "
        "UNION SELECT customer, amount, order_date FROM store_orders)"
    ).fetchone()


def lost_by_union(conn: sqlite3.Connection) -> int:
    """Dollars UNION loses: $5,000 of real sales."""
    _, all_total = combined_all_total(conn)
    _, distinct_total = combined_distinct_total(conn)
    return all_total - distinct_total


def frank_feb2_rows(conn: sqlite3.Connection) -> int:
    """Frank's $5,000 on 2026-02-02 appears twice — and both are real."""
    return conn.execute(
        f"SELECT COUNT(*) FROM ({_COMBINED}) "
        "WHERE customer = 'Frank Lopez' AND amount = 5000 "
        "AND order_date = '2026-02-02'"
    ).fetchone()[0]
