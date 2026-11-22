"""Day 45, problem 4: unpivot — wide back to long.

The wide table monthly_sales_wide holds the pivoted shape, NULL
where a seller had no priced sale that month: David (20000,
NULL, NULL), Frank (15000, 5000, 9000), Irene (NULL, 32000,
NULL). Unpivoting is one UNION ALL branch per month column.

- Keeping the NULLs: 9 rows (3 sellers x 3 months), 4 of them
  with a NULL amount — rows that claim nothing happened.
- Filtering the NULLs: 5 rows, the priced cells only — David-Jan,
  Frank-Jan, Frank-Feb, Frank-Mar, Irene-Feb — totalling $81,000.
- The filtered unpivot is the honest one for totals, but it is
  also a lie by omission: David's February did have an order
  (the pending quote), and no row in the wide table can say so.
"""

from __future__ import annotations

import sqlite3

_UNPIVOT = """
SELECT name, '01' AS month, jan AS amount FROM monthly_sales_wide
UNION ALL
SELECT name, '02', feb FROM monthly_sales_wide
UNION ALL
SELECT name, '03', mar FROM monthly_sales_wide
"""


def unpivot_all(conn: sqlite3.Connection) -> list[tuple[str, str, int | None]]:
    """All 9 cells as rows, NULLs kept, ordered by seller then month."""
    rows = conn.execute(_UNPIVOT + " ORDER BY 1, 2").fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def unpivot_priced(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Only the 5 priced cells, NULLs filtered out."""
    rows = conn.execute(
        "SELECT name, month, amount FROM (" + _UNPIVOT + ") "
        "WHERE amount IS NOT NULL ORDER BY 1, 2"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def unpivot_priced_total(conn: sqlite3.Connection) -> int:
    """Total of the 5 priced unpivoted rows: $81,000."""
    return sum(a for _, _, a in unpivot_priced(conn))


def null_rows_in_unpivot(conn: sqlite3.Connection) -> int:
    """Rows with a NULL amount when NULLs are kept: 4 of 9."""
    return sum(1 for r in unpivot_all(conn) if r[2] is None)
