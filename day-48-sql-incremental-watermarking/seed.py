"""Shared seed data for Day 48: the same company database as Days 35-47,
plus one event stream and the two tables an incremental model needs.

Day 48 is about incremental models and watermarking. A full rebuild
re-reads everything; an incremental load reads only what is new since
the watermark - the MAX(event_ts) of the last successful load. The
trap is late data: an event whose event_ts is before the watermark
but which arrived after the load ran. The new tables are:

- order_events: 10 rows, the same 8 orders plus two more, as
  timestamped events with an arrival time. Event 9 is the late row:
  event_ts 2026-02-11 08:00, arrived_at 2026-02-15 07:30 - its
  event time is before load 1's watermark, but it arrived after
  load 1 ran.
- load_state: starts EMPTY; each load writes the model's watermark.
- mart_daily_sales: starts EMPTY; loads fill it, keyed by
  (sale_date, seller).

Every number below was checked against SQLite:

- Full rebuild (group by DATE(event_ts), seller): 10 rows, $102,000.
- Load 1 (arrived_at <= '2026-02-12 18:00'): 6 events, $72,000;
  watermark = MAX(event_ts) = '2026-02-12 13:30'.
- Naive load 2 (event_ts > watermark, arrived by '2026-02-18 18:00'):
  3 events, $26,000 (Feb 14 Frank $9,000; Feb 16 David $11,000;
  Feb 18 Irene $6,000). Mart after loads 1+2: 9 rows, $98,000 -
  event 9 ($4,000) is missing, so the mart is $4,000 short of the
  $102,000 source total.
- Lookback 3 days (event_ts > datetime(watermark, '-3 days') =
  '2026-02-09 13:30'): 6 events, $42,000 (events 5, 6, 7, 8, 9,
  10). Delete the mart window sale_date >= '2026-02-09' and
  re-insert the window: mart 10 rows, $102,000; running the
  window twice gives the same mart (idempotent). Watermark
  advances to '2026-02-18 15:45'.

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

NEWSLETTER = [
    # (email,) — newsletter signups.
    ("alice@acme.example",),
    ("bob@acme.example",),
    ("carol@acme.example",),
    ("david@acme.example",),
    ("grace@acme.example",),
]

WEBINAR = [
    # (email,) — webinar registrations; 3 overlap with newsletter.
    ("carol@acme.example",),
    ("david@acme.example",),
    ("frank@acme.example",),
    ("grace@acme.example",),
    ("henry@acme.example",),
]

UNSUBSCRIBED = [
    # (email,) — opted out; both are in the newsletter/webinar overlap.
    ("david@acme.example",),
    ("grace@acme.example",),
]

ONLINE_ORDERS = [
    # (customer, amount, order_date) — 4 rows, $57,000.
    ("David Kim", 12000, "2026-01-05"),
    ("Frank Lopez", 15000, "2026-01-20"),
    ("Irene Novak", 25000, "2026-02-10"),
    ("Frank Lopez", 5000, "2026-02-02"),
]

STORE_ORDERS = [
    # (customer, amount, order_date) — 4 rows, $29,000. Frank Lopez
    # bought $5,000 of product on 2026-02-02 in store AND online:
    # two real purchases, one identical-looking row.
    ("Frank Lopez", 5000, "2026-02-02"),
    ("David Kim", 8000, "2026-01-12"),
    ("Irene Novak", 7000, "2026-02-15"),
    ("Frank Lopez", 9000, "2026-03-01"),
]

COMPONENTS = [
    # (parent, child, qty_per_parent, unit_cost) - unit_cost is
    # NULL for assemblies (their cost is the sum of their children)
    # and set for leaf parts only.
    ("Laptop", "Screen", 1, None),
    ("Laptop", "Keyboard", 1, None),
    ("Laptop", "Memory", 2, None),
    ("Laptop", "Battery", 1, None),
    ("Laptop", "Chassis", 1, None),
    ("Screen", "Glass", 1, 40.0),
    ("Screen", "Backlight", 2, 5.0),
    ("Keyboard", "Keycap", 60, 0.5),
    ("Memory", "Chip", 8, 6.0),
    ("Battery", "Cell", 4, 8.0),
    ("Chassis", "Screw", 12, 0.1),
]

MONTHLY_WIDE = [
    # (name, jan, feb, mar) - the pivoted seller x month shape,
    # NULL where a seller had no priced sale that month.
    ("David Kim", 20000, None, None),
    ("Frank Lopez", 15000, 5000, 9000),
    ("Irene Novak", None, 32000, None),
]
CRM_CONTACTS = [
    # (id, name, email, source, created) - the messy CRM import.
    # David 3x, Frank 2x, Irene 2x, Grace 1x: 8 rows, 4 people.
    (1, "David Kim", "david@acme.example", "web", "2026-01-05"),
    (2, "David Kim", "david@acme.example", "import", "2026-01-06"),
    (3, "Frank Lopez", "frank@acme.example", "web", "2026-01-05"),
    (4, "Frank Lopez", "frank@acme.example", "import", "2026-01-07"),
    (5, "Irene Novak", "irene@acme.example", "web", "2026-01-05"),
    (6, "Irene Novak", "irene@acme.example", "web", "2026-01-05"),
    (7, "David Kim", "david@acme.example", "referral", "2026-01-08"),
    (8, "Grace Liu", "grace@acme.example", "web", "2026-01-05"),
]





DIM_EMPLOYEE_SCD = [
    # (employee_id, name, department, region, salary, previous_region,
    #  valid_from, valid_to, is_current) - all current on 2026-01-01.
    (6, "David Kim", "Sales", "East", 95000, None, "2026-01-01", "9999-12-31", 1),
    (7, "Frank Lopez", "Sales", "West", 98000, None, "2026-01-01", "9999-12-31", 1),
    (8, "Irene Novak", "Sales", "East", 175000, None, "2026-01-01", "9999-12-31", 1),
]

STG_EMPLOYEE_CHANGES = [
    # (employee_id, name, department, region, salary, change_type,
    #  effective_date) - the 2026-03-01 batch: David Type 1, Frank
    #  Type 2, Irene Type 3, Grace new. Grace is VP Engineering in
    #  San Francisco, so region West.
    (6, "David Kim", "Sales", "East", 96000, "type1", "2026-03-01"),
    (7, "Frank Lopez", "Data", "West", 115000, "type2", "2026-03-01"),
    (8, "Irene Novak", "Sales", "West", 175000, "type3", "2026-03-01"),
    (1, "Grace Liu", "Engineering", "West", 190000, "new", "2026-03-01"),
]

ORDER_EVENTS = [
    # (event_id, seller, region, amount, event_ts, arrived_at)
    # The same 8 orders as `orders` (new amounts for the two extra
    # events), as timestamped events. Event 9 is the LATE row: its
    # event time (2026-02-11 08:00) is before load 1's watermark,
    # but it arrived (2026-02-15 07:30) after load 1 ran.
    (1, "David Kim", "East", 12000, "2026-02-01 09:12", "2026-02-01 09:15"),
    (2, "Frank Lopez", "West", 15000, "2026-02-03 14:40", "2026-02-03 14:42"),
    (3, "Irene Novak", "East", 25000, "2026-02-05 11:05", "2026-02-05 11:06"),
    (4, "David Kim", "East", 8000, "2026-02-08 16:20", "2026-02-08 16:21"),
    (5, "Frank Lopez", "West", 5000, "2026-02-10 10:00", "2026-02-10 10:01"),
    (6, "Irene Novak", "West", 7000, "2026-02-12 13:30", "2026-02-12 13:31"),
    (7, "Frank Lopez", "East", 9000, "2026-02-14 09:00", "2026-02-14 09:02"),
    (8, "David Kim", "West", 11000, "2026-02-16 12:00", "2026-02-16 12:01"),
    (9, "David Kim", "East", 4000, "2026-02-11 08:00", "2026-02-15 07:30"),
    (10, "Irene Novak", "East", 6000, "2026-02-18 15:45", "2026-02-18 15:46"),
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
    conn.execute(
        """CREATE TABLE newsletter (
            email TEXT PRIMARY KEY)"""
    )
    conn.execute(
        """CREATE TABLE webinar (
            email TEXT PRIMARY KEY)"""
    )
    conn.execute(
        """CREATE TABLE unsubscribed (
            email TEXT PRIMARY KEY)"""
    )
    conn.execute(
        """CREATE TABLE online_orders (
            customer TEXT NOT NULL, amount INTEGER NOT NULL,
            order_date TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE store_orders (
            customer TEXT NOT NULL, amount INTEGER NOT NULL,
            order_date TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE components (
            parent TEXT NOT NULL, child TEXT NOT NULL,
            qty INTEGER NOT NULL, unit_cost REAL)"""
    )
    conn.execute(
        """CREATE TABLE monthly_sales_wide (
            name TEXT PRIMARY KEY, jan INTEGER, feb INTEGER, mar INTEGER)"""
    )
    conn.execute(
        """CREATE TABLE dim_employee_scd (
            employee_id INTEGER NOT NULL, name TEXT NOT NULL,
            department TEXT NOT NULL, region TEXT NOT NULL,
            salary INTEGER NOT NULL, previous_region TEXT,
            valid_from TEXT NOT NULL, valid_to TEXT NOT NULL,
            is_current INTEGER NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE stg_employee_changes (
            employee_id INTEGER NOT NULL, name TEXT NOT NULL,
            department TEXT NOT NULL, region TEXT NOT NULL,
            salary INTEGER NOT NULL, change_type TEXT NOT NULL,
            effective_date TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE crm_contacts (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            email TEXT NOT NULL, source TEXT NOT NULL,
            created TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE order_events (
            event_id INTEGER PRIMARY KEY, seller TEXT NOT NULL,
            region TEXT NOT NULL, amount INTEGER NOT NULL,
            event_ts TEXT NOT NULL, arrived_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE load_state (
            model TEXT PRIMARY KEY, watermark TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE mart_daily_sales (
            sale_date TEXT NOT NULL, seller TEXT NOT NULL,
            total INTEGER NOT NULL,
            PRIMARY KEY (sale_date, seller))"""
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
    conn.executemany("INSERT INTO newsletter VALUES (?)", NEWSLETTER)
    conn.executemany("INSERT INTO webinar VALUES (?)", WEBINAR)
    conn.executemany("INSERT INTO unsubscribed VALUES (?)", UNSUBSCRIBED)
    conn.executemany("INSERT INTO online_orders VALUES (?, ?, ?)", ONLINE_ORDERS)
    conn.executemany("INSERT INTO store_orders VALUES (?, ?, ?)", STORE_ORDERS)
    conn.executemany("INSERT INTO components VALUES (?, ?, ?, ?)", COMPONENTS)
    conn.executemany("INSERT INTO monthly_sales_wide VALUES (?, ?, ?, ?)", MONTHLY_WIDE)
    conn.executemany("INSERT INTO crm_contacts VALUES (?, ?, ?, ?, ?)", CRM_CONTACTS)
    conn.executemany("INSERT INTO dim_employee_scd VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", DIM_EMPLOYEE_SCD)
    conn.executemany("INSERT INTO stg_employee_changes VALUES (?, ?, ?, ?, ?, ?, ?)", STG_EMPLOYEE_CHANGES)
    conn.executemany("INSERT INTO order_events VALUES (?, ?, ?, ?, ?, ?)", ORDER_EVENTS)
    # load_state and mart_daily_sales start EMPTY: loads fill them.
    conn.execute("CREATE INDEX idx_employees_salary ON employees(salary)")
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = create_company_db()
    for table in ("departments", "employees", "projects", "assignments", "project_tags", "orders",
                  "scores", "staged_orders", "employee_refs", "raw_amounts", "staged_raw",
                  "newsletter", "webinar", "unsubscribed", "online_orders", "store_orders",
                  "components", "monthly_sales_wide", "crm_contacts",
                  "dim_employee_scd", "stg_employee_changes",
                  "order_events", "load_state", "mart_daily_sales"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")
