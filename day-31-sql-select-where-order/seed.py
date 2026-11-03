"""Shared seed data for Day 31: a tiny company database in SQLite.

Every Day 31 problem queries this same ``employees`` table, so the
dataset lives here once instead of being copied into five files.
``create_company_db`` returns a fresh in-memory connection — tests
call it per test, so no test can pollute another.

The data is deliberately shaped for the day's lessons:
- 12 employees across 4 departments (Engineering, Sales, Data, HR)
- 4 NULL manager_ids (the department heads) — for IS NULL lessons
- a salary tie (Bob Martinez and Henry Wong, both 110000) — for
  ORDER BY tie-breaking lessons
- repeated titles (Data Engineer x3, Account Executive x2) — for
  DISTINCT lessons
"""

from __future__ import annotations

import sqlite3

EMPLOYEES = [
    # (id, name, department, title, salary, manager_id, hire_date)
    (1, "Grace Liu", "Engineering", "VP Engineering", 190000, None, "2018-04-02"),
    (2, "Alice Chen", "Engineering", "Senior Data Engineer", 145000, 1, "2021-03-15"),
    (3, "Bob Martinez", "Engineering", "Data Engineer", 110000, 1, "2022-06-01"),
    (4, "Carol Davis", "Engineering", "Data Engineer", 112000, 1, "2021-11-20"),
    (5, "Henry Wong", "Engineering", "Data Engineer", 110000, 1, "2023-01-09"),
    (6, "David Kim", "Sales", "Account Executive", 95000, 8, "2020-05-10"),
    (7, "Frank Lopez", "Sales", "Account Executive", 98000, 8, "2021-08-23"),
    (8, "Irene Novak", "Sales", "VP Sales", 175000, None, "2017-09-11"),
    (9, "Jack Thompson", "Data", "Analytics Engineer", 120000, 10, "2022-02-14"),
    (10, "Karen White", "Data", "Head of Data", 160000, None, "2019-06-30"),
    (11, "Leo Garcia", "HR", "Recruiter", 75000, 12, "2023-05-22"),
    (12, "Mia Brown", "HR", "HR Manager", 105000, None, "2020-11-02"),
]


def create_company_db() -> sqlite3.Connection:
    """Build the seeded in-memory company database."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            title TEXT NOT NULL,
            salary INTEGER NOT NULL,
            manager_id INTEGER,
            hire_date TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?)", EMPLOYEES
    )
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = create_company_db()
    rows = conn.execute("SELECT COUNT(*) FROM employees").fetchone()
    print(f"seeded employees: {rows[0]}")
