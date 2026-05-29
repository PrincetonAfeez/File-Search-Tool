"""Test advanced content search features."""

from pathlib import Path

import pytest

from file_search_tool.content import ContentReadCache, _scan_lines, find_content_matches, prepare_content
from file_search_tool.errors import ContentSearchError


def test_prepare_content_reads_text_lines(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("one\ntwo\n", encoding="utf-8")

    prepared = prepare_content(path)

    assert prepared.lines == ["one", "two"]
    assert not prepared.binary_skipped
    assert not prepared.access_error


def test_prepare_content_marks_binary_files(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01")

    prepared = prepare_content(path)

    assert prepared.lines is None
    assert prepared.binary_skipped


def test_prepare_content_only_probes_first_4096_bytes_for_binary(tmp_path: Path):
    path = tmp_path / "late.bin"
    path.write_bytes(b"a" * 5000 + b"\x00")

    prepared = prepare_content(path)

    assert not prepared.binary_skipped
    assert prepared.lines is not None
    assert len(prepared.lines[0]) >= 5000


def test_content_read_cache_clear_allows_reread(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("v1", encoding="utf-8")
    cache = ContentReadCache()

    first = cache.prepare(path, "skip")
    cache.clear()
    path.write_text("v2", encoding="utf-8")
    second = cache.prepare(path, "skip")

    assert first is not second
    assert second.lines == ["v2"]


def test_scan_lines_finds_plain_and_regex_matches():
    lines = ["TODO item", "nothing"]
    plain = _scan_lines(lines, "TODO", regex=False, case_sensitive=True, compiled_regex=None)
    regex = _scan_lines(lines, r"TODO\s+\w+", regex=True, case_sensitive=True, compiled_regex=None)

    assert plain[0].matched_text == "TODO"
    assert regex[0].matched_text == "TODO item"


def test_case_insensitive_match_inside_expanded_char():
    out = _scan_lines(["a\u00dfb"], "sb", regex=False, case_sensitive=False, compiled_regex=None)

    assert len(out) == 1
    assert out[0].matched_text == "\u00dfb"


def test_find_content_matches_with_regex(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("print('TODO')\n", encoding="utf-8")

    outcome = find_content_matches(path, r"TODO", regex=True)

    assert outcome.matches[0].line_number == 1


def test_prepare_content_binary_error_raises(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01")

    with pytest.raises(ContentSearchError, match="binary file not searchable"):
        prepare_content(path, binary_policy="error")


def test_prepare_content_access_error(tmp_path: Path):
    missing = tmp_path / "missing.txt"

    prepared = prepare_content(missing)

    assert prepared.access_error
    assert prepared.lines is None
