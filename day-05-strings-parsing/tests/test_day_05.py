"""Day 5 tests — every solution must pass before the day is committed."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_quoted_csv_fields import parse_fields
from problem_02_log_extractor import is_error_line, parse_log_line
from problem_03_invisible_cleaner import clean_text
from problem_04_safe_decode import looks_mojibake, safe_decode
from problem_05_streaming_parser import RowValidationError, stream_rows


# --- Problem 1: parse_fields -------------------------------------------------

def test_01_quoted_comma_stays_one_field():
    assert parse_fields('Alice,"42 Main St, Apt 3",Springfield') == [
        "Alice", "42 Main St, Apt 3", "Springfield",
    ]


def test_01_doubled_quotes_unescape():
    assert parse_fields('"say ""hi""",42') == ['say "hi"', "42"]


def test_01_whitespace_stripped_and_empties_kept():
    assert parse_fields('  ORD-42  ,, 19.99 ') == ["ORD-42", "", "19.99"]


def test_01_unbalanced_quote_fails_fast():
    with pytest.raises(ValueError):
        parse_fields('name,addr"ess,city')


def test_01_custom_delimiter():
    assert parse_fields("a;\"b;c\";d", delimiter=";") == ["a", "b;c", "d"]


# --- Problem 2: log parsing ---------------------------------------------------

def test_02_full_line_parses():
    assert parse_log_line("2026-10-08 07:12:44 [ERROR] disk full on /data") == {
        "ts": "2026-10-08 07:12:44", "level": "ERROR", "msg": "disk full on /data",
    }


def test_02_missing_level_ok():
    parsed = parse_log_line("2026-10-08 07:12:44 heartbeat ok")
    assert parsed["level"] is None
    assert parsed["msg"] == "heartbeat ok"


def test_02_garbage_line_returns_none():
    assert parse_log_line("--- rotated at midnight ---") is None


def test_02_error_prefilter():
    assert is_error_line("2026-10-08 07:12:44 [ERROR] boom") is True
    assert is_error_line("2026-10-08 07:12:44 [INFO] fine") is False
    # the word ERROR without brackets is not a level tag
    assert is_error_line("2026-10-08 07:12:44 ERROR-ish") is False


def test_02_regex_compiled_once():
    import problem_02_log_extractor as m
    assert hasattr(m.LOG_RE, "match")  # a compiled pattern, not re.match per line


# --- Problem 3: invisible cleaner ----------------------------------------------

def test_03_zero_width_space_removed():
    assert clean_text("  Alice\u200b  ") == "Alice"


def test_03_bom_and_nbsp_handled():
    assert clean_text("\ufeffORD-42\u00a0") == "ORD-42"


def test_03_whitespace_runs_collapsed():
    assert clean_text("a\t\tb\n c") == "a b c"


def test_03_blank_returns_empty_never_raises():
    assert clean_text("   ") == ""
    assert clean_text("") == ""


def test_03_soft_hyphen_removed():
    assert clean_text("co\u00adop") == "coop"


# --- Problem 4: safe decode -----------------------------------------------------

def test_04_utf8_decodes():
    assert safe_decode(b"caf\xc3\xa9") == "café"


def test_04_bad_byte_replaced_not_raised():
    assert safe_decode(b"ok\xffbad") == "ok�bad"


def test_04_str_passes_through():
    assert safe_decode("already text") == "already text"


def test_04_mojibake_heuristic():
    assert looks_mojibake("cafÃ©") is True
    assert looks_mojibake("café") is False
    assert looks_mojibake("") is False


# --- Problem 5: streaming parser --------------------------------------------------

def _write(tmp_path, content):
    p = tmp_path / "feed.csv"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_05_streams_and_skips_blanks(tmp_path):
    path = _write(tmp_path, 'a,"b,c",d\n\nx,y,z\n')
    assert list(stream_rows(path, 3)) == [["a", "b,c", "d"], ["x", "y", "z"]]


def test_05_short_row_fails_fast_with_line_no(tmp_path):
    path = _write(tmp_path, "a,b,c\nd,e\n")
    with pytest.raises(RowValidationError) as exc_info:
        list(stream_rows(path, 3))
    assert exc_info.value.line_no == 2
    assert "expected 3 columns, got 2" in str(exc_info.value)


def test_05_is_lazy_generator(tmp_path):
    import types
    path = _write(tmp_path, "a,b,c\n")
    gen = stream_rows(path, 3)
    assert isinstance(gen, types.GeneratorType)


def test_05_large_file_fast_and_flat(tmp_path):
    path = tmp_path / "big.csv"
    with open(path, "w", encoding="utf-8") as f:
        for i in range(200_000):
            f.write(f"{i},name-{i},ok\n")
    start = time.time()
    count = sum(1 for _ in stream_rows(str(path), 3))
    elapsed = time.time() - start
    assert count == 200_000
    assert elapsed < 15  # streaming: seconds, not minutes; memory flat
