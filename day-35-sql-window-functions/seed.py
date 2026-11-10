"""Shared seed data for Day 35: the same company database as Day 34,
unchanged — window functions are about how you *number*, not new data.

Day 34 nested and named queries. Day 35 numbers rows without collapsing
them: ROW_NUMBER, RANK, and DENSE_RANK over PARTITION BY / ORDER BY.
The dataset is built so the ranking traps bite:

- the Bob/Henry tie at $110,000 in Engineering is the whole lesson:
  ROW_NUMBER must pick one (4 vs 5), RANK gives both 8, DENSE_RANK
  gives both 8 with no gap after.

- employees: 13 rows, unchanged (5 Engineering, 3 Sales, 2 Data,
  2 HR, 1 Legal). Department averages are exact and checkable by
  hand: Engineering 133,400; Sales ~122,667; Data 140,000; HR 90,000;
  Legal 125,000; company average ~124,615.38.
- manager_id: the org chart. Five people have no manager (Grace,
  Irene, Karen, Mia, Nina); the other eight report to one of them.
  The NULLs in manager_id are the whole NOT IN trap: NOT IN over a
  set containing NULL returns nothing at all.
- assignments / projects: Apollo 35h, Beacon 33h, Cypress 28h;
  Delta has no assignments. Active projects are Apollo and Beacon.
- orders: 8 rows, one NULL amount (David's pending quote).
  East totals 54,000; West totals 27,000.

``create_company_db`` returns a fresh in-memory connection per call,
so tests stay independent.
"""

from __future__ import annotations

import sqlite3

DEPARTMENTS = [
    # (dept_name, location, budget)
    ("Engineering", "San Francisco", 5000000),
    ("Sales", "New York", 3000000),
    ("Data", "Austin", 2500000),
    ("HR", "Remote", 1000000),
    ("Operations", "Chicago", 2000000),
]

EMPLOYEES = [
    # (id, name, department, title, salary, manager_id)
    (1, "Grace Liu", "Engineering", "VP Engineering", 190000, None),
    (2, "Alice Chen", "Engineering", "Senior Data Engineer", 145000, 1),
    (3, "Bob Martinez", "Engineering", "Data Engineer", 110000, 1),
    (4, "Carol Davis", "Engineering", "Data Engineer", 112000, 1),
    (5, "Henry Wong", "Engineering", "Data Engineer", 110000, 1),
    (6, "David Kim", "Sales", "Account Executive", 95000, 8),
    (7, "Frank Lopez", "Sales", "Account Executive", 98000, 8),
    (8, "Irene Novak", "Sales", "VP Sales", 175000, None),
    (9, "Jack Thompson", "Data", "Analytics Engineer", 120000, 10),
    (10, "Karen White", "Data", "Head of Data", 160000, None),
    (11, "Leo Garcia", "HR", "Recruiter", 75000, 12),
    (12, "Mia Brown", "HR", "HR Manager", 105000, None),
    (13, "Nina Patel", "Legal", "Counsel", 125000, None),
]

PROJECTS = [
    # (project_id, project_name, status)
    (1, "Apollo", "active"),
    (2, "Beacon", "active"),
    (3, "Cypress", "completed"),
    (4, "Delta", "planning"),
]

ASSIGNMENTS = [
    # (employee_id, project_id, hours)
    (2, 1, 20),  # Alice -> Apollo
    (2, 2, 15),  # Alice -> Beacon
    (3, 1, 10),  # Bob -> Apollo
    (4, 1, 5),  # Carol -> Apollo
    (4, 3, 8),  # Carol -> Cypress
    (1, 2, 12),  # Grace -> Beacon
    (9, 3, 20),  # Jack -> Cypress
    (6, 2, 6),  # David -> Beacon
]

PROJECT_TAGS = [
    # (project_id, tag)
    (1, "ml"),
    (1, "realtime"),  # Apollo has TWO tags -> fanout doubling
    (2, "streaming"),
    (3, "batch"),
]

ORDERS = [
    # (order_id, employee_id, region, amount, order_date)
    # amount NULL on order 7: a pending quote, not a zero sale.
    (1, 6, "East", 12000, "2026-01-05"),  # David
    (2, 6, "East", 8000, "2026-01-12"),  # David
    (3, 7, "West", 15000, "2026-01-20"),  # Frank
    (4, 7, "West", 5000, "2026-02-02"),  # Frank
    (5, 8, "East", 25000, "2026-02-10"),  # Irene
    (6, 8, "West", 7000, "2026-02-15"),  # Irene
    (7, 6, "West", None, "2026-02-20"),  # David, pending quote
    (8, 7, "East", 9000, "2026-03-01"),  # Frank
]


def create_company_db() -> sqlite3.Connection:
    """Build the seeded in-memory company database."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE departments (
            dept_name TEXT PRIMARY KEY, location TEXT NOT NULL, budget INTEGER NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE employees (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, department TEXT NOT NULL,
            title TEXT NOT NULL, salary INTEGER NOT NULL, manager_id INTEGER)"""
    )
    conn.execute(
        """CREATE TABLE projects (
            project_id INTEGER PRIMARY KEY, project_name TEXT NOT NULL,
            status TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE assignments (
            employee_id INTEGER NOT NULL, project_id INTEGER NOT NULL,
            hours INTEGER NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE project_tags (
            project_id INTEGER NOT NULL, tag TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL,
            region TEXT NOT NULL, amount INTEGER, order_date TEXT NOT NULL)"""
    )
    conn.executemany("INSERT INTO departments VALUES (?, ?, ?)", DEPARTMENTS)
    conn.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)", EMPLOYEES)
    conn.executemany("INSERT INTO projects VALUES (?, ?, ?)", PROJECTS)
    conn.executemany("INSERT INTO assignments VALUES (?, ?, ?)", ASSIGNMENTS)
    conn.executemany("INSERT INTO project_tags VALUES (?, ?)", PROJECT_TAGS)
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = create_company_db()
    for table in ("departments", "employees", "projects", "assignments", "project_tags", "orders"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")
