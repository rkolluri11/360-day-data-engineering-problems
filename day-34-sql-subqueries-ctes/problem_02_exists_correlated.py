"""Day 34 - Problem 2: EXISTS and the NOT IN NULL trap.

EXISTS asks a yes/no question per row: "is there at least one row
over there that matches this one?" It stops at the first match, it
never counts, and — critically — it is immune to NULLs. NOT IN is
not: one NULL in the list poisons every comparison to UNKNOWN, and
the query silently returns zero rows.

Beginner foothold: EXISTS is a bouncer checking a guest list.
"Is this person on any active project?" The bouncer looks for one
matching name and waves them through. NOT IN is a bouncer with a
list that has a smudged, unreadable entry — faced with a name they
cannot read, they refuse *everyone*, just in case. That is exactly
what SQL does: `id NOT IN (1, 8, 10, 12, NULL)` is UNKNOWN for every
id, and WHERE keeps only TRUE rows — so nothing comes back.

The trap is live in this dataset: manager_id is NULL for the five
top-level people, so NOT IN over manager_id returns []. NOT EXISTS
returns the correct 9 non-managers. In production this is the bug
that makes a "customers with no orders" report come back empty the
week a single order row gets a NULL customer id.
"""

from __future__ import annotations

import sqlite3


def on_active_project(conn: sqlite3.Connection) -> list[str]:
    """Employees with at least one assignment on an active project.

    Correlated EXISTS: for each employee, look for one assignment
    joined to a project whose status is 'active'. Alice Chen, Bob
    Martinez, Carol Davis, David Kim, Grace Liu — 5 people. Jack
    Thompson is excluded: his only assignment is Cypress, which is
    'completed'. Frank Lopez, Henry Wong, Irene Novak, Karen White,
    Leo Garcia, Mia Brown and Nina Patel have no assignments at all.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees e
            WHERE EXISTS (
                SELECT 1
                FROM assignments a
                JOIN projects p ON p.project_id = a.project_id
                WHERE a.employee_id = e.id
                  AND p.status = 'active'
            )
            ORDER BY name ASC
            """
        ).fetchall()
    ]


def with_no_assignment(conn: sqlite3.Connection) -> list[str]:
    """Employees with no assignment on any project (NOT EXISTS).

    Frank Lopez, Henry Wong, Irene Novak, Karen White, Leo Garcia,
    Mia Brown, Nina Patel — 7 people. NOT EXISTS is the safe way to
    ask "has none of these": it reads as what it means, and NULLs
    cannot poison it.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees e
            WHERE NOT EXISTS (
                SELECT 1 FROM assignments a
                WHERE a.employee_id = e.id
            )
            ORDER BY name ASC
            """
        ).fetchall()
    ]


def departments_with_high_earner(
    conn: sqlite3.Connection, threshold: int = 150000
) -> list[str]:
    """Departments where at least one employee clears ``threshold``.

    EXISTS over the departments table: Data (Karen White, 160,000),
    Engineering (Grace Liu, 190,000), Sales (Irene Novak, 175,000).
    HR tops out at 105,000 and Legal at 125,000. Operations has no
    employees, so no earner can exist there.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT dept_name
            FROM departments d
            WHERE EXISTS (
                SELECT 1 FROM employees e
                WHERE e.department = d.dept_name
                  AND e.salary > ?
            )
            ORDER BY dept_name ASC
            """,
            (threshold,),
        ).fetchall()
    ]


def non_managers_via_not_in(conn: sqlite3.Connection) -> list[str]:
    """Employees who manage nobody — asked the WRONG way (NOT IN).

    Returns [] — always, regardless of the data. manager_id contains
    NULLs (the five top-level people have no manager), so the IN list
    is (1, 8, 10, 12, NULL, ...) and `id NOT IN (...)` evaluates to
    UNKNOWN for every employee. WHERE drops UNKNOWN rows. This
    function exists so the trap is documented and tested, not
    repeated: never use NOT IN on a column that can be NULL.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees
            WHERE id NOT IN (SELECT manager_id FROM employees)
            ORDER BY name ASC
            """
        ).fetchall()
    ]


def non_managers_via_not_exists(conn: sqlite3.Connection) -> list[str]:
    """Employees who manage nobody — asked the RIGHT way (NOT EXISTS).

    Alice Chen, Bob Martinez, Carol Davis, David Kim, Frank Lopez,
    Henry Wong, Jack Thompson, Leo Garcia, Nina Patel — 9 people.
    The four managers are Grace Liu, Irene Novak, Karen White and
    Mia Brown (13 - 4 = 9). Same question as non_managers_via_not_in,
    correct answer.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM employees e
            WHERE NOT EXISTS (
                SELECT 1 FROM employees s
                WHERE s.manager_id = e.id
            )
            ORDER BY name ASC
            """
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("on active project:       ", on_active_project(conn))
    print("with no assignment:      ", with_no_assignment(conn))
    print("depts with >150k earner: ", departments_with_high_earner(conn))
    print("non-managers via NOT IN:     ", non_managers_via_not_in(conn))
    print("non-managers via NOT EXISTS: ", non_managers_via_not_exists(conn))
