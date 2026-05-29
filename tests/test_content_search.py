"""Test the content search functionality."""

from pathlib import Path

import pytest

from file_search_tool import content as content_module
from file_search_tool.content import ContentReadCache, compile_content_regex, find_content_matches
from file_search_tool.errors import ContentSearchError
from file_search_tool.filters import AndPredicate, ContentPredicate, NamePredicate, OrPredicate
from file_search_tool.models import FileEntry, SearchStats
from file_search_tool.search import search_with_stats


def test_empty_content_pattern_is_rejected():
    with pytest.raises(ContentSearchError, match="cannot be empty"):
        ContentPredicate("")


def test_invalid_content_regex_is_rejected():
    with pytest.raises(ContentSearchError, match="invalid content regex"):
        compile_content_regex("[")


def test_content_read_cache_reads_each_file_once(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\n", encoding="utf-8")
    cache = ContentReadCache()

    first = cache.prepare(path, "skip")
    second = cache.prepare(path, "skip")

    assert first is second


def test_and_content_predicates_share_one_read_per_entry(tmp_path: Path, monkeypatch):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\nbravo\n", encoding="utf-8")

    calls: list[Path] = []
    original = content_module.prepare_content

    def counting_prepare(target: Path, binary_policy: str):
        calls.append(target)
        return original(target, binary_policy)

    monkeypatch.setattr(content_module, "prepare_content", counting_prepare)

    predicate = AndPredicate([ContentPredicate("alpha"), ContentPredicate("bravo")])
    list(search_with_stats(tmp_path, predicate).results)

    assert calls.count(path) == 1


def test_content_cache_does_not_grow_on_non_matching_entries(tmp_path: Path):
    for index in range(10):
        (tmp_path / f"note{index}.txt").write_text("alpha\n", encoding="utf-8")

    content = ContentPredicate("alpha")
    predicate = AndPredicate([content, NamePredicate("*.py")])

    list(search_with_stats(tmp_path, predicate).results)

    assert content._matches_by_path == {}


def test_record_binary_skip_counts_once_per_path():
    stats = SearchStats()
    path = Path("data.bin")

    assert stats.record_binary_skip(path) is True
    assert stats.record_binary_skip(path) is False
    assert stats.binary_files_skipped == 1


def test_content_search_returns_line_numbers(tmp_path: Path):
    path = tmp_path / "todo.txt"
    path.write_text("one\nTODO item\nthree\n", encoding="utf-8")

    outcome = find_content_matches(path, "TODO")

    assert not outcome.binary_skipped
    assert not outcome.access_error
    assert outcome.matches[0].line_number == 2
    assert outcome.matches[0].line_text == "TODO item"


def test_content_search_can_ignore_case(tmp_path: Path):
    path = tmp_path / "todo.txt"
    path.write_text("todo item\n", encoding="utf-8")

    outcome = find_content_matches(path, "TODO", case_sensitive=False)

    assert len(outcome.matches) == 1


def test_content_search_case_insensitive_preserves_original_matched_text(tmp_path: Path):
    path = tmp_path / "gross.txt"
    path.write_text("gro\u00df stuff\n", encoding="utf-8")

    outcome = find_content_matches(path, "gross", case_sensitive=False)

    assert len(outcome.matches) == 1
    assert outcome.matches[0].matched_text == "gro\u00df"


def test_content_search_case_insensitive_turkish_dotless_i(tmp_path: Path):
    path = tmp_path / "city.txt"
    path.write_text("\u0130stanbul\n", encoding="utf-8")

    outcome = find_content_matches(path, "i", case_sensitive=False)

    assert len(outcome.matches) == 1
    assert outcome.matches[0].matched_text == "\u0130"


def test_content_search_case_insensitive_literal_regex_matches_unicode(tmp_path: Path):
    path = tmp_path / "gross.txt"
    path.write_text("gro\u00df stuff\n", encoding="utf-8")

    outcome = find_content_matches(path, "gross", regex=True, case_sensitive=False)

    assert len(outcome.matches) == 1
    assert outcome.matches[0].matched_text == "gro\u00df"


def test_content_search_skips_binary_files(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc\x00def")

    outcome = find_content_matches(path, "abc")

    assert outcome.matches == []
    assert outcome.binary_skipped


def test_content_search_reports_access_errors(tmp_path: Path):
    path = tmp_path / "missing.txt"

    outcome = find_content_matches(path, "abc")

    assert outcome.matches == []
    assert outcome.access_error


def test_content_predicate_updates_binary_skip_stats(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc\x00def")
    item = FileEntry(path, tmp_path, path.relative_to(tmp_path), True, False, False, 7, 1.0, 1)
    stats = SearchStats()
    predicate = ContentPredicate("abc")
    predicate.bind_stats(stats)

    assert not predicate.matches(item)
    assert stats.binary_files_skipped == 1


def test_or_content_counts_binary_skip_once(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"alpha\x00beta")
    stats = SearchStats()
    combined = OrPredicate([ContentPredicate("alpha"), ContentPredicate("beta")])
    combined.bind_stats(stats)
    entry = FileEntry(path, tmp_path, path.relative_to(tmp_path), True, False, False, 7, 1.0, 1)

    assert not combined.matches(entry)
    assert stats.binary_files_skipped == 1
