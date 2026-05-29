"""Test advanced filter features."""

from pathlib import Path

import pytest

from file_search_tool.content import ContentMatch
from file_search_tool.errors import ContentSearchError, InvalidFilterError
from file_search_tool.filters import (
    AlwaysTruePredicate,
    AndPredicate,
    ContentPredicate,
    ExtensionPredicate,
    NamePredicate,
    NotPredicate,
    OrPredicate,
    PathPredicate,
    SizePredicate,
    TypePredicate,
    _intersect_content_match_lists,
    combine_with_and,
)
from file_search_tool.models import FileEntry, SearchStats
from file_search_tool.sizeparse import parse_size_expression


def entry(path: Path, root: Path, *, is_file=True, is_dir=False, is_symlink=False):
    return FileEntry(
        path=path,
        root=root,
        relative_path=path.relative_to(root),
        is_file=is_file,
        is_dir=is_dir,
        is_symlink=is_symlink,
        size=10 if is_file else None,
        mtime=1.0,
        depth=1,
    )


def test_intersect_content_match_lists_empty_input():
    assert _intersect_content_match_lists([]) == []


def test_intersect_content_match_lists_no_shared_lines():
    left = [ContentMatch(1, "alpha", "alpha")]
    right = [ContentMatch(2, "beta", "beta")]

    assert _intersect_content_match_lists([left, right]) == []


def test_combine_with_and_empty_returns_always_true():
    predicate = combine_with_and([])

    assert isinstance(predicate, AlwaysTruePredicate)


def test_path_predicate_supports_regex(tmp_path: Path):
    path = tmp_path / "src" / "app.py"
    path.parent.mkdir(parents=True)
    path.write_text("", encoding="utf-8")
    item = entry(path, tmp_path)

    assert PathPredicate(r"src/app\.py$", regex=True).matches(item)


def test_type_predicate_matches_directory(tmp_path: Path):
    directory = tmp_path / "pkg"
    directory.mkdir()

    assert TypePredicate("dir").matches(entry(directory, tmp_path, is_file=False, is_dir=True))


def test_type_predicate_rejects_unknown_type(tmp_path: Path):
    item = entry(tmp_path / "app.py", tmp_path)

    assert TypePredicate("unknown").matches(item) is False


def test_content_predicate_skips_directories_and_symlinks(tmp_path: Path):
    directory = tmp_path / "docs"
    directory.mkdir()
    predicate = ContentPredicate("x")

    assert predicate.matches(entry(directory, tmp_path, is_file=False, is_dir=True)) is False
    assert predicate.collect_content_matches(entry(directory, tmp_path, is_file=False, is_dir=True)) == []


def test_content_predicate_reports_missing_file_access_error(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    stats = SearchStats()
    warnings: list[str] = []
    predicate = ContentPredicate("needle")
    predicate.bind_stats(stats, warnings)

    assert predicate.matches(entry(missing, tmp_path)) is False
    assert stats.permission_errors == 1
    assert warnings


def test_content_predicate_regex_mode(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("TODO item\n", encoding="utf-8")
    predicate = ContentPredicate(r"TODO\s+\w+", regex=True)

    assert predicate.matches(entry(path, tmp_path)) is True


def test_or_predicate_deduplicates_identical_content_matches(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\n", encoding="utf-8")
    item = entry(path, tmp_path)
    combined = OrPredicate([ContentPredicate("alpha"), ContentPredicate("alpha")])

    assert combined.matches(item)
    matches = combined.collect_content_matches(item)

    assert len(matches) == 1


def test_and_predicate_collects_single_content_group(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\n", encoding="utf-8")
    item = entry(path, tmp_path)
    combined = AndPredicate([NamePredicate("*.txt"), ContentPredicate("alpha")])

    assert combined.matches(item)
    matches = combined.collect_content_matches(item)

    assert len(matches) == 1


def test_not_predicate_collect_returns_empty(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\n", encoding="utf-8")
    item = entry(path, tmp_path)
    combined = NotPredicate(ContentPredicate("alpha"))

    assert combined.collect_content_matches(item) == []


def test_size_predicate_on_directory_returns_false(tmp_path: Path):
    directory = tmp_path / "empty"
    directory.mkdir()
    predicate = SizePredicate(parse_size_expression("+1B"))

    assert predicate.matches(entry(directory, tmp_path, is_file=False, is_dir=True)) is False


def test_extension_predicate_normalizes_dotted_extensions():
    predicate = ExtensionPredicate([".PY"], case_sensitive=False)

    assert ".py" in predicate._extensions


def test_content_predicate_binary_error_raises(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01")
    predicate = ContentPredicate("x", binary_policy="error")

    with pytest.raises(ContentSearchError, match="binary file not searchable"):
        predicate.matches(entry(path, tmp_path))


def test_record_binary_skip_without_stats_does_not_crash(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00")
    predicate = ContentPredicate("x")

    assert predicate.matches(entry(path, tmp_path)) is False


def test_content_predicate_records_access_error_without_warnings(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    stats = SearchStats()
    predicate = ContentPredicate("needle")
    predicate.bind_stats(stats, None)

    assert predicate.matches(entry(missing, tmp_path)) is False
    assert stats.permission_errors == 1


def test_content_predicate_records_binary_skip_without_warnings(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00")
    stats = SearchStats()
    predicate = ContentPredicate("x")
    predicate.bind_stats(stats, None)

    assert predicate.matches(entry(path, tmp_path)) is False
    assert stats.binary_files_skipped == 1


def test_name_predicate_invalid_regex_raises():
    with pytest.raises(InvalidFilterError):
        NamePredicate("[", regex=True)
