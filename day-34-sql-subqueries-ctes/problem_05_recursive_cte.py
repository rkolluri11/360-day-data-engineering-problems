"""Day 34 - Problem 5: Recursive CTE — walk the org chart.

A recursive CTE is a CTE that refers to itself: an anchor step
produces the first rows, and a recursive step keeps adding rows
until nothing new appears. It is the SQL way to walk a tree — an
org chart, a category hierarchy, a bill of materials — without
knowing in advance how deep the tree goes.

Beginner foothold: the anchor is "everyone with no manager" (the
roots). The recursive step is "everyone whose manager is already
in the list, one level deeper". Run the step once: the direct
reports appear. Run it again: their reports appear. Stop when a
run adds nobody. The database does the looping; you write two
SELECTs and a UNION ALL.

This org is shallow — five roots at depth 0, eight people at depth
1, nobody deeper — which is exactly why the test asserts max depth
1: if a future seed row ever made the tree deeper, the same query
still works, and the test would catch the changed shape. The team
rollup reuses the same walk to total each manager's whole subtree:
Grace Liu's team of 4 earns 477,000; Irene Novak's team of 2 earns
193,000; Karen White's 1 earns 120,000; Mia Brown's 1 earns 75,000.
"""

from __future__ import annotations

import sqlite3


def org_depths(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """Every employee with their depth in the org chart.

    Recursive CTE: anchor = the five people with no manager
    (depth 0); recursive step = employees whose manager is already
    listed, at depth + 1. Grace Liu, Irene Novak, Karen White, Mia
    Brown, Nina Patel at 0; Alice Chen, Bob Martinez, Carol Davis,
    David Kim, Frank Lopez, Henry Wong, Jack Thompson, Leo Garcia
    at 1. Ordered by depth, then name.
    """
    return conn.execute(
        """
        WITH RECURSIVE org(id, name, depth) AS (
            SELECT id, name, 0
            FROM employees
            WHERE manager_id IS NULL
            UNION ALL
            SELECT e.id, e.name, o.depth + 1
            FROM employees e
            JOIN org o ON e.manager_id = o.id
        )
        SELECT name, depth
        FROM org
        ORDER BY depth ASC, name ASC
        """
    ).fetchall()


def max_org_depth(conn: sqlite3.Connection) -> int:
    """Deepest level in the org chart (0 = top-level only).

    1: the chart is two levels — five roots, eight direct reports,
    no grand-reports. A deeper company would return a bigger number
    from the identical query; that is the point of recursion.
    """
    return conn.execute(
        """
        WITH RECURSIVE org(id, depth) AS (
            SELECT id, 0
            FROM employees
            WHERE manager_id IS NULL
            UNION ALL
            SELECT e.id, o.depth + 1
            FROM employees e
            JOIN org o ON e.manager_id = o.id
        )
        SELECT MAX(depth) FROM org
        """
    ).fetchone()[0]


def team_rollup(conn: sqlite3.Connection) -> list[tuple[str, int, int]]:
    """Per manager: size of their whole subtree and its total salary.

    Recursive CTE: anchor = every direct report (manager, employee,
    salary); recursive step = reports of people already in the team.
    Grace Liu: 4 reports, 477,000. Irene Novak: 2, 193,000. Karen
    White: 1, 120,000. Mia Brown: 1, 75,000. Nina Patel manages
    nobody, so she has no row — a rollup over teams cannot invent a
    team. (In this two-level org the subtree equals the direct
    reports; the recursion is what makes it stay correct when a
    third level appears.)
    """
    return conn.execute(
        """
        WITH RECURSIVE team(mgr, emp, salary) AS (
            SELECT manager_id, id, salary
            FROM employees
            WHERE manager_id IS NOT NULL
            UNION ALL
            SELECT t.mgr, e.id, e.salary
            FROM team t
            JOIN employees e ON e.manager_id = t.emp
        )
        SELECT m.name, COUNT(*), SUM(t.salary)
        FROM team t
        JOIN employees m ON m.id = t.mgr
        GROUP BY m.name
        ORDER BY m.name ASC
        """
    ).fetchall()


def manager_chain(conn: sqlite3.Connection, employee_id: int) -> list[str]:
    """The chain of managers above one employee, nearest first.

    Walks *up* the tree: anchor = the employee's own manager,
    recursive step = that manager's manager. Alice Chen (id 2)
    -> ["Grace Liu"]. Leo Garcia (id 11) -> ["Mia Brown"]. Grace
    Liu (id 1) -> [] — she has no manager. A chain that hit a cycle
    would loop forever in a naive walk; this dataset has none, and
    the empty-chain case is the base case the recursion must handle.
    """
    return [
        row[0]
        for row in conn.execute(
            """
            WITH RECURSIVE chain(id, name, mgr) AS (
                SELECT id, name, manager_id
                FROM employees
                WHERE id = ?
                UNION ALL
                SELECT e.id, e.name, e.manager_id
                FROM employees e
                JOIN chain c ON e.id = c.mgr
            )
            SELECT name FROM chain WHERE id != ?
            """,
            (employee_id, employee_id),
        ).fetchall()
    ]


if __name__ == "__main__":
    from seed import create_company_db

    conn = create_company_db()
    print("org depths:   ", org_depths(conn))
    print("max depth:    ", max_org_depth(conn))
    print("team rollup:  ", team_rollup(conn))
    print("Alice's chain:", manager_chain(conn, 2))
    print("Grace's chain:", manager_chain(conn, 1))
