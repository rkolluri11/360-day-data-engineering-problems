"""Day 38 - Problem 5: NOT IN is poisoned by one NULL — use NOT EXISTS.

Five people have no manager — Grace, Irene, Karen, Mia, Nina —
so manager_id contains NULLs. Ask who is NOT a manager with
``NOT IN (SELECT manager_id FROM employees)`` and you get 0 rows:
one NULL in the list makes every comparison UNKNOWN, and WHERE
drops UNKNOWN. Guard it with ``manager_id IS NOT NULL``, or use
``NOT EXISTS`` — immune to the trap, and the semi-join Day 43
builds on. Both fixes return the real 9 non-managers.
"""

from __future__ import annotations

import sqlite3

NON_MANAGERS = [
    "Alice Chen",
    "Bob Martinez",
    "Carol Davis",
    "David Kim",
    "Frank Lopez",
    "Henry Wong",
    "Jack Thompson",
    "Leo Garcia",
    "Nina Patel",
]


def not_in_count(conn: sqlite3.Connection) -> int:
    """Rows from the naive NOT IN — 0, the trap."""
    return conn.execute(
        """
        SELECT COUNT(*) FROM employees
        WHERE id NOT IN (SELECT manager_id FROM employees)
        """
    ).fetchone()[0]


def not_in_fixed(conn: sqlite3.Connection) -> list[str]:
    """NOT IN guarded with IS NOT NULL — the real 9 non-managers."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM employees
            WHERE id NOT IN (
                SELECT manager_id FROM employees
                WHERE manager_id IS NOT NULL
            )
            ORDER BY name ASC
            """
        ).fetchall()
    ]


def not_exists_non_managers(conn: sqlite3.Connection) -> list[str]:
    """NOT EXISTS — immune to the NULL, same 9 names."""
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM employees e
            WHERE NOT EXISTS (
                SELECT 1 FROM employees m
                WHERE m.manager_id = e.id
            )
            ORDER BY name ASC
            """
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("NOT IN count:", not_in_count(conn))
    print("NOT IN fixed:", not_in_fixed(conn))
    print("NOT EXISTS:", not_exists_non_managers(conn))
