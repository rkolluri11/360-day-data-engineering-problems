"""Day 41, problem 2: UPPER/LOWER — normalize identity.

TRIM alone is not enough: 'David Kim', 'david kim', and 'FRANK
LOPEZ ' are still different strings after trimming, because SQL
string comparison is case-sensitive. UPPER (or LOWER) collapses the
case, and the combination UPPER(TRIM(...)) is the standard
normalize-first step before a GROUP BY or a join on a dirty
text key. Regions are the same story: 7 raw spellings of East and
West collapse to 2, and only then do the totals match the clean
orders table — East $54,000, West $27,000.
"""

from __future__ import annotations

import sqlite3


def customer_order_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Orders per normalized customer: David Kim 3, Frank Lopez 3, Irene Novak 2."""
    rows = conn.execute(
        "SELECT UPPER(TRIM(customer_raw)), COUNT(*) FROM staged_raw "
        "GROUP BY UPPER(TRIM(customer_raw)) ORDER BY 1"
    ).fetchall()
    return {name.title(): count for name, count in rows}


def distinct_regions_raw(conn: sqlite3.Connection) -> int:
    """Distinct region spellings before cleaning: 7."""
    return conn.execute(
        "SELECT COUNT(DISTINCT region_raw) FROM staged_raw"
    ).fetchone()[0]


def region_totals(conn: sqlite3.Connection) -> dict[str, int]:
    """Total cleaned amount per normalized region: East $54,000, West $27,000."""
    rows = conn.execute(
        """SELECT UPPER(TRIM(region_raw)),
                  SUM(CAST(NULLIF(REPLACE(REPLACE(amount_text, ',', ''), '$', ''), 'N/A') AS INTEGER))
           FROM staged_raw GROUP BY UPPER(TRIM(region_raw)) ORDER BY 1"""
    ).fetchall()
    return {region.title(): total for region, total in rows}


def region_order_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Orders per normalized region: East 4, West 4."""
    rows = conn.execute(
        "SELECT UPPER(TRIM(region_raw)), COUNT(*) FROM staged_raw "
        "GROUP BY UPPER(TRIM(region_raw)) ORDER BY 1"
    ).fetchall()
    return {region.title(): count for region, count in rows}
