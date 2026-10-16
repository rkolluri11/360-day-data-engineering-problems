"""Day 13 tests — every solution must pass before the day is committed."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_annotate_the_contract import (
    describe_signature,
    extract,
    load,
    prove_runtime_ignores,
)
from problem_02_shape_the_row import (
    EventRow,
    RawRow,
    check_raw_row,
    row_shape,
    validate_row,
)
from problem_03_name_the_absence import coalesce, parse_amount, total_amounts
from problem_04_type_the_containers import (
    batch_stats,
    compose,
    count_by,
    top_n,
)
from problem_05_check_before_runtime import (
    HintViolation,
    add_amounts,
    check_call,
    check_return,
    greet,
)


# --- Problem 1: annotate the contract ---------------------------------------


def test_01_contract_names_every_parameter():
    contract = describe_signature(load)
    assert contract == {"rows": "list[dict]", "dest": "str", "return": "int"}


def test_01_extract_contract():
    assert describe_signature(extract) == {
        "source": "str",
        "return": "list[dict]",
    }


def test_01_annotations_are_metadata():
    assert set(load.__annotations__) == {"rows", "dest", "return"}


def test_01_runtime_ignores_hints():
    # len("abc") == 3: the call runs despite wrong types. Hints don't gate.
    assert prove_runtime_ignores() == 3


def test_01_unannotated_is_reported():
    def bare(x):
        return x

    assert describe_signature(bare) == {"x": "unannotated", "return": "unannotated"}


# --- Problem 2: shape the row -------------------------------------------------


def test_02_row_shape_reads_typeddict():
    assert row_shape(RawRow) == {"user_id": "str", "amount": "str"}


def test_02_event_row_marks_optional_keys():
    shape = row_shape(EventRow)
    assert shape == {"user_id": "str", "amount": "str", "currency": "str"}
    assert EventRow.__total__ is False  # all keys optional by default


def test_02_clean_row_has_no_problems():
    assert check_raw_row({"user_id": "u-1", "amount": "10.5"}) == []


def test_02_missing_key_is_flagged():
    assert check_raw_row({"user_id": "u-2", "discount": "5"}) == [
        "missing: amount",
        "unexpected: discount",
    ]


def test_02_extra_allowed_key_passes():
    assert check_raw_row({"user_id": "u-1", "amount": "1", "currency": "USD"}) == []


def test_02_validate_row_is_deterministic():
    problems = validate_row({"z": 1}, {"b", "a"}, {"c"})
    assert problems == ["missing: a", "missing: b", "unexpected: z"]


# --- Problem 3: name the absence ----------------------------------------------


def test_03_parse_amount_happy_path():
    assert parse_amount("10.5") == 10.5


def test_03_parse_amount_none_and_blank():
    assert parse_amount(None) is None
    assert parse_amount("") is None
    assert parse_amount("   ") is None


def test_03_coalesce_first_non_none_wins():
    assert coalesce(None, None, 3) == 3
    assert coalesce(None, None) is None
    assert coalesce(0, 5) == 0  # 0 is a value, not absence


def test_03_total_amounts_skips_nones():
    assert total_amounts(["1", None, "2.5", "", "3"]) == 6.5


def test_03_total_amounts_all_absent():
    assert total_amounts([None, ""]) == 0.0


# --- Problem 4: type the containers -------------------------------------------


def test_04_count_by_builds_counter():
    rows = [
        {"tier": "pro"},
        {"tier": "free"},
        {"tier": "pro"},
    ]
    assert count_by(rows, "tier") == {"pro": 2, "free": 1}


def test_04_top_n_ranks_and_truncates():
    assert top_n({"pro": 2, "free": 1, "team": 5}, 2) == [
        ("team", 5),
        ("pro", 2),
    ]


def test_04_compose_wires_stages_in_order():
    def only_pro(rs):
        return [r for r in rs if r["tier"] == "pro"]

    def tag(rs):
        return [{**r, "tagged": "yes"} for r in rs]

    rows = [{"tier": "pro"}, {"tier": "free"}]
    assert compose(only_pro, tag)(rows) == [
        {"tier": "pro", "tagged": "yes"}
    ]


def test_04_batch_stats_nested_generics():
    assert batch_stats({"s1": [1.0, 3.0], "s2": [2.0]}) == {"s1": 2.0, "s2": 2.0}


def test_04_compose_empty_is_identity():
    rows = [{"a": "1"}]
    assert compose()(rows) == rows


# --- Problem 5: check before runtime -------------------------------------------


def test_05_checked_call_passes():
    assert check_call(add_amounts, 1.0, 2.0) == 3.0


def test_05_checked_call_rejects_wrong_type():
    with pytest.raises(HintViolation) as exc:
        check_call(add_amounts, "1", 2.0)
    assert 'Argument "a"' in str(exc.value)
    assert "expected" in str(exc.value)


def test_05_union_branch_none_allowed():
    assert check_call(greet, None) == "hi there"
    assert check_call(greet, "sam") == "hi sam"


def test_05_checked_call_with_kwargs():
    assert check_call(add_amounts, a=1.0, b=2.0) == 3.0
    with pytest.raises(HintViolation):
        check_call(add_amounts, a=1.0, b="x")


def test_05_check_return_validates():
    assert check_return(add_amounts, 3.0) == 3.0
    with pytest.raises(HintViolation):
        check_return(add_amounts, "not-a-float")


def test_05_hint_violation_is_a_type_error():
    assert issubclass(HintViolation, TypeError)
