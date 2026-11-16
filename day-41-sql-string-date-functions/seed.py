"""Shared seed data for Day 41: the same company database as Days 35-40,
plus one dirty staging table.

Day 41 is about string and date functions on messy source data. The
same 8 orders from Days 38-40 were loaded dirty into staged_raw —
same amounts, same dates, same regions — but with leading/trailing
spaces, mixed case, commas, a dollar sign, an 'N/A' sentinel, and
three different date formats. Every number below was checked
against SQLite:

- staged_raw: 8 rows, columns (order_id, customer_raw, amount_text,
  date_text, region_raw).
- TRIM: COUNT(DISTINCT customer_raw) is 7 raw, 6 after TRIM, 3 after
  UPPER(TRIM). LENGTH('  David Kim ') is 12, TRIM is 9.
- identity: UPPER(TRIM(customer_raw)) gives David Kim 3, Frank Lopez
  3, Irene Novak 2; 7 raw region spellings collapse to East/West —
  East 4 orders $54,000, West 4 orders $27,000.
- CAST: CAST('12,000' AS INTEGER) is 12, CAST('$25,000') is 0,
  naive SUM(CAST(amount_text)) is 15,041. REPLACE ',' and '$' out
  first, then CAST, and the sum is $81,000.
- NULLIF: CAST('N/A' AS INTEGER) is 0. On cleaned amounts without
  NULLIF, COUNT is 8 and AVG is 10,125; with NULLIF the 'N/A'
  becomes NULL, COUNT is 7 and AVG is 11,571.43.
- dates: DATE(date_text) parses only 3 of 8 (the ISO ones). Rebuild
  MM/DD/YYYY with SUBSTR and 'Jan 20, 2026' with a month-name CASE
  and all 8 land on the clean order dates: Jan 3 orders $35,000,
  Feb 4 orders $37,000, Mar 1 order $9,000; julianday span 55 days.

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


SCORES = [
    # (name, score_text) — scores stored as TEXT on purpose.
    ("Priya", "9"),
    ("Quinn", "10"),
    ("Rosa", "100"),
    ("Sam", "20"),
    ("Tara", "7"),
]

STAGED_ORDERS = [
    # (order_id, amount_text) — the Day 38 orders, amounts as TEXT.
    (1, "12000"),
    (2, "8000"),
    (3, "15000"),
    (4, "5000"),
    (5, "25000"),
    (6, "7000"),
    (7, None),  # David, pending quote — still NULL
    (8, "9000"),
]

EMPLOYEE_REFS = [
    # (id_text, code) — plain text ids next to zero-padded HR codes.
    (str(i), f"{i:03d}")
    for i in range(1, 14)
]

RAW_AMOUNTS = [
    # (raw_text,) — dirty strings a CAST has to chew on.
    ("12000",),
    ("12,500",),
    ("12.9",),
    ("abc",),
    ("",),
]

STAGED_RAW = [
    # (order_id, customer_raw, amount_text, date_text, region_raw)
    # The same 8 orders as `orders`, loaded dirty: spaces, mixed case,
    # commas, a dollar sign, an 'N/A' sentinel, three date formats.
    (1, "  David Kim ", "12,000", "2026-01-05", "east "),
    (2, "david kim", "8000", "01/12/2026", "EAST"),
    (3, "Frank Lopez", "15,000", "Jan 20, 2026", "west"),
    (4, "FRANK LOPEZ ", "5,000", "2026-02-02", " West"),
    (5, "Irene Novak", "$25,000", "02/10/2026", "EAST"),
    (6, "irene novak", "7000", "Feb 15, 2026", "west "),
    (7, "David Kim", "N/A", "2026-02-20", "WEST"),
    (8, "Frank Lopez", "9,000", "03/01/2026", "east"),
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
    conn.execute(
        """CREATE TABLE scores (
            name TEXT NOT NULL, score_text TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE staged_orders (
            order_id INTEGER PRIMARY KEY, amount_text TEXT)"""
    )
    conn.execute(
        """CREATE TABLE employee_refs (
            id_text TEXT NOT NULL, code TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE raw_amounts (
            raw_text TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE staged_raw (
            order_id INTEGER PRIMARY KEY, customer_raw TEXT NOT NULL,
            amount_text TEXT NOT NULL, date_text TEXT NOT NULL,
            region_raw TEXT NOT NULL)"""
    )
    conn.executemany("INSERT INTO departments VALUES (?, ?, ?)", DEPARTMENTS)
    conn.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)", EMPLOYEES)
    conn.executemany("INSERT INTO projects VALUES (?, ?, ?)", PROJECTS)
    conn.executemany("INSERT INTO assignments VALUES (?, ?, ?)", ASSIGNMENTS)
    conn.executemany("INSERT INTO project_tags VALUES (?, ?)", PROJECT_TAGS)
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
    conn.executemany("INSERT INTO scores VALUES (?, ?)", SCORES)
    conn.executemany("INSERT INTO staged_orders VALUES (?, ?)", STAGED_ORDERS)
    conn.executemany("INSERT INTO employee_refs VALUES (?, ?)", EMPLOYEE_REFS)
    conn.executemany("INSERT INTO raw_amounts VALUES (?)", RAW_AMOUNTS)
    conn.executemany("INSERT INTO staged_raw VALUES (?, ?, ?, ?, ?)", STAGED_RAW)
    conn.execute("CREATE INDEX idx_employees_salary ON employees(salary)")
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = create_company_db()
    for table in ("departments", "employees", "projects", "assignments", "project_tags", "orders",
                  "scores", "staged_orders", "employee_refs", "raw_amounts", "staged_raw"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")
