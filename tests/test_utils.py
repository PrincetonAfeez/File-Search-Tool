"""Test the utils."""

from pathlib import Path

from file_search_tool.utils import (
    entry_type,
    is_hidden_relative,
    matches_any_pattern,
    normalize_relative_path,
    relative_to_root,
    sort_key_text,
    split_csv_values,
)


def test_relative_to_root_falls_back_to_name():
    root = Path("/search/root")
    outside = Path("/elsewhere/file.txt")

    assert relative_to_root(outside, root) == Path("file.txt")


def test_normalize_relative_path_maps_empty_to_dot():
    assert normalize_relative_path(Path("")) == "."


def test_entry_type_reports_known_kinds():
    assert entry_type(is_file=False, is_dir=False, is_symlink=True) == "symlink"
    assert entry_type(is_file=False, is_dir=True, is_symlink=False) == "dir"
    assert entry_type(is_file=True, is_dir=False, is_symlink=False) == "file"
    assert entry_type(is_file=False, is_dir=False, is_symlink=False) == "other"


def test_sort_key_text_respects_case_sensitivity():
    assert sort_key_text("AbC", case_sensitive=True) == "AbC"
    assert sort_key_text("AbC", case_sensitive=False) == "abc"


def test_split_csv_values_handles_none_and_empty():
    assert split_csv_values(None) == []
    assert split_csv_values("") == []
    assert split_csv_values("  ") == []
    assert split_csv_values(" py , md , ") == ["py", "md"]


def test_is_hidden_relative_detects_dotfiles():
    assert is_hidden_relative(Path(".git/config"))
    assert not is_hidden_relative(Path("src/app.py"))


def test_matches_any_pattern_checks_name_and_path():
    assert matches_any_pattern("SkipMe.txt", Path("src/SkipMe.txt"), ["SKIPME.*"], case_sensitive=False)
    assert not matches_any_pattern("keep.txt", Path("src/keep.txt"), ["SKIPME.*"], case_sensitive=False)


def test_matches_any_pattern_case_sensitive():
    assert matches_any_pattern("File.txt", Path("File.txt"), ["file.*"], case_sensitive=True) is False
    assert matches_any_pattern("File.txt", Path("File.txt"), ["file.*"], case_sensitive=False)

