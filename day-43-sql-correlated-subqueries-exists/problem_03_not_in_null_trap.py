"""Day 43, problem 3: NOT IN vs NOT EXISTS — the NULL that eats the answer.

``NOT IN`` looks like the mirror of ``IN``, but it is not: it is
three-valued logic in disguise. The manager list is
``SELECT manager_id FROM employees`` — and 5 top-level staff have
no manager, so the list contains a NULL. For every employee, the
check becomes ``id <> 1 AND id <> 8 AND ... AND id <> NULL``,
and ``id <> NULL`` is UNKNOWN, so the whole row is UNKNOWN and
no row survives. NOT IN over a list containing NULL returns
0 rows — not "everyone who is not a manager", but nobody at all.

NOT EXISTS has no such trap: it asks "is there a row where this
person is someone's manager?" and a NULL manager_id simply never
matches. The 9 people who manage nobody come back cleanly. The
positive side is unaffected — IN over the same NULL-containing
list still finds the 4 managers (Grace, Irene, Karen, Mia),
because IN only needs one TRUE match while NOT IN needs every
comparison to be TRUE.

Rule of thumb: NOT IN is safe only when you can prove the list
has no NULLs. If the column is nullable — and manager_id always
is — use NOT EXISTS.
"""

from __future__ import annotations

import sqlite3


def managers_via_in(conn: sqlite3.Connection) -> list[str]:
    """People who are someone's manager, via IN: 4 names."""
    rows = conn.execute(
        "SELECT name FROM employees "
        "WHERE id IN (SELECT manager_id FROM employees) ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def non_managers_via_not_in(conn: sqlite3.Connection) -> list[str]:
    """People who manage nobody, via NOT IN: 0 rows — the NULL poisons it."""
    rows = conn.execute(
        "SELECT name FROM employees "
        "WHERE id NOT IN (SELECT manager_id FROM employees) ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def non_managers_via_not_exists(conn: sqlite3.Connection) -> list[str]:
    """People who manage nobody, via NOT EXISTS: the correct 9."""
    rows = conn.execute(
        "SELECT e.name FROM employees e "
        "WHERE NOT EXISTS (SELECT 1 FROM employees x WHERE x.manager_id = e.id) "
        "ORDER BY e.name"
    ).fetchall()
    return [r[0] for r in rows]


def null_manager_count(conn: sqlite3.Connection) -> int:
    """Employees with no manager (NULL manager_id): 5 top-level staff."""
    return conn.execute(
        "SELECT COUNT(*) FROM employees WHERE manager_id IS NULL"
    ).fetchone()[0]


def non_managers_via_not_in_filtered(conn: sqlite3.Connection) -> list[str]:
    """NOT IN with the NULL filtered out: the same correct 9.

    Adding ``WHERE manager_id IS NOT NULL`` fixes NOT IN — proof
    the NULL was the whole problem, not the logic.
    """
    rows = conn.execute(
        "SELECT name FROM employees "
        "WHERE id NOT IN (SELECT manager_id FROM employees "
        "WHERE manager_id IS NOT NULL) ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]
