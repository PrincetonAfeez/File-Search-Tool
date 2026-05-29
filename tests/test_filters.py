"""Test the filters."""

from pathlib import Path

import pytest

from file_search_tool.errors import InvalidFilterError
from file_search_tool.filters import (
    BasePredicate,
    ExtensionPredicate,
    NamePredicate,
    PathPredicate,
    TypePredicate,
)
from file_search_tool.models import FileEntry


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


def test_name_glob_matches(tmp_path: Path):
    item = entry(tmp_path / "app.py", tmp_path)

    assert NamePredicate("*.py").matches(item)
    assert not NamePredicate("*.md").matches(item)


def test_regex_name_matches(tmp_path: Path):
    item = entry(tmp_path / "test_app.py", tmp_path)

    assert NamePredicate(r"^test_.*\.py$", regex=True).matches(item)


def test_extension_filter_matches_comma_parts(tmp_path: Path):
    item = entry(tmp_path / "notes.MD", tmp_path)

    assert ExtensionPredicate(["py", "md"], case_sensitive=False).matches(item)


def test_empty_extension_list_is_rejected():
    with pytest.raises(InvalidFilterError, match="extension list cannot be empty"):
        ExtensionPredicate([])
    with pytest.raises(InvalidFilterError, match="extension list cannot be empty"):
        ExtensionPredicate([",", " "])


def test_base_predicate_matches_raises_not_implemented(tmp_path: Path):
    item = entry(tmp_path / "app.py", tmp_path)

    with pytest.raises(NotImplementedError):
        BasePredicate().matches(item)


def test_type_filter_prefers_symlink_type(tmp_path: Path):
    item = entry(tmp_path / "link", tmp_path, is_file=False, is_symlink=True)

    assert TypePredicate("symlink").matches(item)
    assert not TypePredicate("file").matches(item)


def test_path_filter_uses_posix_paths(tmp_path: Path):
    (tmp_path / "src").mkdir()
    path = tmp_path / "src" / "app.py"
    path.write_text("", encoding="utf-8")
    item = entry(path, tmp_path)

    assert PathPredicate("src/*.py").matches(item)

