"""Day 44 tests: SQL recursive CTEs — walk the tree in one query.

Same company database as Days 35-43, plus a components table for
one laptop's bill of materials. All expected numbers were computed
against the seed and checked by hand: org levels depth 0 = 5 roots,
depth 1 = 8 reports, max depth 1; subtrees (anchor included)
Grace 5 people / $667,000, Irene 3 / $368,000, Karen 2 / $280,000,
Mia 2 / $180,000, Nina 1 / $125,000; paths Alice "Grace Liu >
Alice Chen", Leo "Mia Brown > Leo Garcia", David "Irene Novak >
David Kim"; 1 laptop explodes to 95 leaf parts across 6 types for
$209.20 (Glass 1, Backlight 2, Keycap 60, Chip 16, Cell 4,
Screw 12); 10 laptops: 950 parts, $2,092.00; 12 distinct parts.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_org_levels import (
    direct_reports,
    max_depth,
    org_levels,
    people_at_depth,
    roots,
)
from problem_02_subtree import (
    all_subtree_totals,
    descendants_only,
    subtree,
    subtree_headcount,
    subtree_salary_total,
)
from problem_03_paths import depth_for, path_for, paths
from problem_04_bom_explosion import (
    bom_explosion,
    bom_leaves,
    bom_leaf_total_cost,
    bom_leaf_total_units,
)
from problem_05_guards_and_scale import (
    bom_scaled,
    bom_with_depth_cap,
    cyclic_traversal_terminates,
    distinct_parts,
)
from seed import create_company_db


@pytest.fixture
def conn():
    return create_company_db()


def test_levels_are_five_roots_and_eight_reports(conn):
    assert org_levels(conn) == [(0, 5), (1, 8)]


def test_roots_are_the_five_people_with_no_manager(conn):
    assert roots(conn) == ["Grace Liu", "Irene Novak", "Karen White", "Mia Brown", "Nina Patel"]


def test_people_at_each_depth(conn):
    assert people_at_depth(conn, 0) == roots(conn)
    assert people_at_depth(conn, 1) == [
        "Alice Chen", "Bob Martinez", "Carol Davis", "David Kim",
        "Frank Lopez", "Henry Wong", "Jack Thompson", "Leo Garcia",
    ]


def test_max_depth_is_one_flat_org(conn):
    assert max_depth(conn) == 1


def test_direct_reports_is_one_level_only(conn):
    assert direct_reports(conn, 1) == ["Alice Chen", "Bob Martinez", "Carol Davis", "Henry Wong"]
    assert direct_reports(conn, 13) == []


def test_grace_subtree_is_five_people(conn):
    assert [name for name, _ in subtree(conn, 1)] == [
        "Grace Liu", "Alice Chen", "Bob Martinez", "Carol Davis", "Henry Wong",
    ]
    assert subtree_headcount(conn, 1) == 5
    assert subtree_salary_total(conn, 1) == 667000


def test_other_subtrees(conn):
    assert (subtree_headcount(conn, 8), subtree_salary_total(conn, 8)) == (3, 368000)
    assert (subtree_headcount(conn, 10), subtree_salary_total(conn, 10)) == (2, 280000)
    assert (subtree_headcount(conn, 12), subtree_salary_total(conn, 12)) == (2, 180000)
    assert (subtree_headcount(conn, 13), subtree_salary_total(conn, 13)) == (1, 125000)


def test_descendants_exclude_the_anchor(conn):
    assert descendants_only(conn, 1) == ["Alice Chen", "Bob Martinez", "Carol Davis", "Henry Wong"]
    assert len(descendants_only(conn, 1)) == subtree_headcount(conn, 1) - 1


def test_all_subtree_totals(conn):
    assert all_subtree_totals(conn) == [
        ("Grace Liu", 5, 667000),
        ("Irene Novak", 3, 368000),
        ("Karen White", 2, 280000),
        ("Mia Brown", 2, 180000),
        ("Nina Patel", 1, 125000),
    ]


def test_paths_are_breadcrumbs(conn):
    assert path_for(conn, "Alice Chen") == "Grace Liu > Alice Chen"
    assert path_for(conn, "Leo Garcia") == "Mia Brown > Leo Garcia"
    assert path_for(conn, "David Kim") == "Irene Novak > David Kim"
    assert path_for(conn, "Grace Liu") == "Grace Liu"
    assert depth_for(conn, "Alice Chen") == 1
    assert depth_for(conn, "Grace Liu") == 0


def test_paths_cover_all_thirteen(conn):
    assert len(paths(conn)) == 13
    assert all(depth in (0, 1) for _, _, depth in paths(conn))


def test_bom_explosion_has_twelve_rows(conn):
    rows = bom_explosion(conn)
    assert len(rows) == 12
    assert rows[0] == ("Laptop", 1, 0)
    by_part = {part: (qty, depth) for part, qty, depth in rows}
    assert by_part["Memory"] == (2, 1)
    assert by_part["Chip"] == (16, 2)
    assert by_part["Keycap"] == (60, 2)


def test_bom_leaves_are_six_types(conn):
    assert bom_leaves(conn) == [
        ("Backlight", 2, 5.0, 10.0),
        ("Cell", 4, 8.0, 32.0),
        ("Chip", 16, 6.0, 96.0),
        ("Glass", 1, 40.0, 40.0),
        ("Keycap", 60, 0.5, 30.0),
        ("Screw", 12, 0.1, pytest.approx(1.2)),
    ]


def test_bom_totals_for_one_laptop(conn):
    assert bom_leaf_total_units(conn) == 95
    assert bom_leaf_total_cost(conn) == pytest.approx(209.20)


def test_bom_scales_to_ten_laptops(conn):
    assert bom_scaled(conn, "Laptop", 10) == (950, pytest.approx(2092.0))
    assert bom_scaled(conn, "Laptop", 1) == (95, pytest.approx(209.20))


def test_depth_cap_stops_at_sub_assemblies(conn):
    rows = bom_with_depth_cap(conn, cap=1)
    assert len(rows) == 6
    assert all(depth <= 1 for _, _, depth in rows)
    assert ("Screen", 1, 1) in rows
    assert ("Glass", 1, 2) not in rows


def test_depth_cap_zero_is_just_the_anchor(conn):
    assert bom_with_depth_cap(conn, cap=0) == [("Laptop", 1, 0)]


def test_distinct_parts_are_twelve(conn):
    assert distinct_parts(conn) == [
        "Backlight", "Battery", "Cell", "Chassis", "Chip", "Glass",
        "Keyboard", "Keycap", "Laptop", "Memory", "Screen", "Screw",
    ]


def test_cyclic_traversal_terminates_with_the_guard(conn):
    count, deepest = cyclic_traversal_terminates(conn, cap=9)
    assert deepest == 9
    assert count > 12  # the loop revisits parts until the cap stops it
