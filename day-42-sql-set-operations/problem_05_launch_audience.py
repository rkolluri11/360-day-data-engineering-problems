"""Day 42, problem 5: combined — build the launch audience.

The real query chains all three set operations. The launch audience
is everyone who signed up anywhere, minus everyone who opted out:
(newsletter UNION webinar) EXCEPT unsubscribed. UNION dedups the
3 people on both lists, EXCEPT removes david and grace, and the
audience is 5: alice, bob, carol, frank, henry.

Two traps live in this one query. First, counting before dedup:
UNION ALL over the two lists reports 10 "contacts" for 7 people —
a dashboard built on that count overstates reach by 43%. Second,
EXCEPT (like UNION and INTERSECT) always returns distinct rows,
so running it over the UNION ALL stack still lands on the same
5 people; the dedup happens whether you asked for it or not.
The safe habit: dedup with UNION, filter with EXCEPT, and only
use UNION ALL when you have proven the duplicates are real events
(Day 42, problem 2).
"""

from __future__ import annotations

import sqlite3


def launch_audience(conn: sqlite3.Connection) -> list[str]:
    """(newsletter UNION webinar) EXCEPT unsubscribed: 5 emails."""
    rows = conn.execute(
        "SELECT email FROM newsletter UNION SELECT email FROM webinar "
        "EXCEPT SELECT email FROM unsubscribed ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def naive_contact_count(conn: sqlite3.Connection) -> int:
    """UNION ALL count across both lists: 10 rows for 7 people — overstated reach."""
    return conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT email FROM newsletter UNION ALL SELECT email FROM webinar)"
    ).fetchone()[0]


def true_reach(conn: sqlite3.Connection) -> int:
    """Distinct people across both lists: 7."""
    return conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT email FROM newsletter UNION SELECT email FROM webinar)"
    ).fetchone()[0]


def audience_via_union_all(conn: sqlite3.Connection) -> list[str]:
    """Same audience built over a UNION ALL stack: still 5 — EXCEPT dedups.

    (newsletter UNION ALL webinar) EXCEPT unsubscribed returns the
    same 5 emails, because EXCEPT returns distinct rows. The dedup
    is free, but the intermediate COUNT(*) would still be wrong —
    count the result, never the stack.
    """
    rows = conn.execute(
        "SELECT email FROM ("
        "SELECT email FROM newsletter UNION ALL SELECT email FROM webinar) "
        "EXCEPT SELECT email FROM unsubscribed ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def opted_out_overlap(conn: sqlite3.Connection) -> list[str]:
    """Unsubscribed people who were in the combined audience: david, grace.

    Both opted-out contacts had signed up on both lists — removing
    them after the UNION catches them once, in one place.
    """
    rows = conn.execute(
        "SELECT email FROM newsletter UNION SELECT email FROM webinar "
        "INTERSECT SELECT email FROM unsubscribed ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]
