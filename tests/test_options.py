"""Test the options."""

from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

import pytest

from file_search_tool.errors import CLIError
from file_search_tool.filters import AndPredicate, ContentPredicate, NamePredicate
from file_search_tool.options import options_from_namespace, predicate_from_namespace


def test_predicate_from_namespace_regex_name(tmp_path: Path):
    (tmp_path / "test_app.py").write_text("", encoding="utf-8")
    (tmp_path / "app.py").write_text("", encoding="utf-8")

    args = Namespace(
        name=None,
        regex_name=r"^test_.*\.py$",
        path_pattern=None,
        ext=None,
        entry_type=None,
        size=None,
        modified_before=None,
        modified_after=None,
        modified_within=None,
        contains=None,
        contains_regex=None,
        query=None,
    )
    search_options, _ = options_from_namespace(
        Namespace(
            ignore_case=False,
            case_sensitive=False,
            content_ignore_case=False,
            binary_error=False,
            depth=None,
            limit=None,
            include_hidden=False,
            follow_symlinks=False,
            exclude=None,
            sort=None,
            output_format="plain",
            summary=False,
            verbose=False,
        )
    )
    predicate = predicate_from_namespace(args, search_options)

    assert isinstance(predicate, NamePredicate)
    assert predicate.regex is True


def test_predicate_from_namespace_modified_flags(tmp_path: Path):
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    old = datetime.now(timezone.utc) - timedelta(days=30)
    recent_path = tmp_path / "recent.txt"
    old_path = tmp_path / "old.txt"
    recent_path.write_text("", encoding="utf-8")
    old_path.write_text("", encoding="utf-8")
    os.utime(recent_path, (recent.timestamp(), recent.timestamp()))
    os.utime(old_path, (old.timestamp(), old.timestamp()))

    args = Namespace(
        name="*.txt",
        regex_name=None,
        path_pattern=None,
        ext=None,
        entry_type=None,
        size=None,
        modified_before=None,
        modified_after=(recent - timedelta(days=2)).strftime("%Y-%m-%d"),
        modified_within="7d",
        contains=None,
        contains_regex=None,
        query=None,
    )
    base = Namespace(
        ignore_case=False,
        case_sensitive=False,
        content_ignore_case=False,
        binary_error=False,
        depth=None,
        limit=None,
        include_hidden=False,
        follow_symlinks=False,
        exclude=None,
        sort=None,
        output_format="plain",
        summary=False,
        verbose=False,
    )
    search_options, _ = options_from_namespace(base)
    predicate = predicate_from_namespace(args, search_options)

    from file_search_tool.search import search_with_stats

    matched = {result.relative_path.name for result in search_with_stats(tmp_path, predicate).results}

    assert matched == {"recent.txt"}


def test_predicate_from_namespace_type_and_contains_regex(tmp_path: Path):
    (tmp_path / "app.py").write_text("TODO item\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("nothing\n", encoding="utf-8")

    args = Namespace(
        name=None,
        regex_name=None,
        path_pattern=None,
        ext=None,
        entry_type="file",
        size=None,
        modified_before=None,
        modified_after=None,
        modified_within=None,
        contains=None,
        contains_regex="TODO",
        query=None,
    )
    base = Namespace(
        ignore_case=False,
        case_sensitive=False,
        content_ignore_case=False,
        binary_error=False,
        depth=None,
        limit=None,
        include_hidden=False,
        follow_symlinks=False,
        exclude=None,
        sort=None,
        output_format="plain",
        summary=False,
        verbose=False,
    )
    search_options, _ = options_from_namespace(base)
    predicate = predicate_from_namespace(args, search_options)

    assert isinstance(predicate, AndPredicate)
    from file_search_tool.search import search_with_stats

    results = list(search_with_stats(tmp_path, predicate).results)
    assert any(result.relative_path.name == "app.py" for result in results)
    assert all(result.relative_path.name != "notes.txt" for result in results)


def test_options_rejects_conflicting_case_flags():
    args = Namespace(
        ignore_case=True,
        case_sensitive=True,
        content_ignore_case=False,
        binary_error=False,
        depth=None,
        limit=None,
        include_hidden=False,
        follow_symlinks=False,
        exclude=None,
        sort=None,
        output_format="plain",
        summary=False,
        verbose=False,
    )

    with pytest.raises(CLIError, match="cannot use --ignore-case and --case-sensitive together"):
        options_from_namespace(args)


def test_options_content_ignore_case_applies_to_contains(tmp_path: Path):
    path = tmp_path / "Notes.txt"
    path.write_text("todo item\n", encoding="utf-8")

    args = Namespace(
        name=None,
        regex_name=None,
        path_pattern=None,
        ext=None,
        entry_type=None,
        size=None,
        modified_before=None,
        modified_after=None,
        modified_within=None,
        contains="TODO",
        contains_regex=None,
        query=None,
    )
    base = Namespace(
        ignore_case=False,
        case_sensitive=True,
        content_ignore_case=True,
        binary_error=False,
        depth=None,
        limit=None,
        include_hidden=False,
        follow_symlinks=False,
        exclude=None,
        sort=None,
        output_format="plain",
        summary=False,
        verbose=False,
    )
    search_options, _ = options_from_namespace(base)
    predicate = predicate_from_namespace(args, search_options)

    assert isinstance(predicate, ContentPredicate)
    assert predicate.case_sensitive is False


def test_predicate_from_namespace_path_and_modified_before(tmp_path: Path):
    from datetime import datetime, timedelta, timezone
    import os

    target = tmp_path / "src" / "old.txt"
    target.parent.mkdir()
    target.write_text("", encoding="utf-8")
    old = datetime.now(timezone.utc) - timedelta(days=30)
    os.utime(target, (old.timestamp(), old.timestamp()))
    (tmp_path / "src" / "new.txt").write_text("", encoding="utf-8")

    args = Namespace(
        name=None,
        regex_name=None,
        path_pattern="src/*",
        ext=None,
        entry_type=None,
        size=None,
        modified_before=(datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
        modified_after=None,
        modified_within=None,
        contains=None,
        contains_regex=None,
        query=None,
    )
    base = Namespace(
        ignore_case=False,
        case_sensitive=False,
        content_ignore_case=False,
        binary_error=False,
        depth=None,
        limit=None,
        include_hidden=False,
        follow_symlinks=False,
        exclude=None,
        sort=None,
        output_format="plain",
        summary=False,
        verbose=False,
    )
    search_options, _ = options_from_namespace(base)
    predicate = predicate_from_namespace(args, search_options)

    from file_search_tool.search import search_with_stats

    matched = {result.relative_path.as_posix() for result in search_with_stats(tmp_path, predicate).results}

    assert "src/old.txt" in matched
    assert "src/new.txt" not in matched


def test_effective_content_case_sensitive_uses_search_default():
    from file_search_tool.models import SearchOptions
    from file_search_tool.options import effective_content_case_sensitive

    assert effective_content_case_sensitive(SearchOptions(case_sensitive=False)) is False
    assert effective_content_case_sensitive(
        SearchOptions(case_sensitive=True, content_case_sensitive=False)
    ) is False
