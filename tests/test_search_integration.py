"""Test the search integration."""

from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
import os
import sys

import pytest

from file_search_tool.cli import build_parser, run
from file_search_tool.dsl import compile_ast, parse_query
from file_search_tool.errors import CLIError
from file_search_tool.filters import ContentPredicate, combine_with_and
from file_search_tool.formatters import tree as tree_formatter
from file_search_tool.models import FileEntry, SearchOptions, SearchResult, SearchStats
from file_search_tool.options import options_from_namespace, predicate_from_namespace
from file_search_tool.search import search_with_stats, sync_stats_for_output
from file_search_tool.traversal import walk


def make_entry(path: Path, root: Path) -> FileEntry:
    stat_result = path.stat()
    return FileEntry(
        path=path,
        root=root,
        relative_path=path.relative_to(root),
        is_file=True,
        is_dir=False,
        is_symlink=False,
        size=stat_result.st_size,
        mtime=stat_result.st_mtime,
        depth=1,
    )


def test_or_content_shows_lines_when_name_branch_matches_first(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("print('TODO')\n", encoding="utf-8")
    predicate = compile_ast(parse_query("name:*.py OR contains:TODO"))

    session = search_with_stats(tmp_path, predicate)
    output = list(session.results)

    assert any(result.match_kind == "content" and "TODO" in (result.line_text or "") for result in output)


def test_or_content_shows_lines_from_both_contains_branches(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\nbravo\n", encoding="utf-8")
    predicate = compile_ast(parse_query("contains:alpha OR contains:bravo"))

    session = search_with_stats(tmp_path, predicate)
    lines = [result.line_text for result in session.results if result.match_kind == "content"]

    assert "alpha" in lines
    assert "bravo" in lines


def test_and_multiple_contains_emits_only_shared_lines(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha only\nalpha and bravo\nbravo only\n", encoding="utf-8")
    predicate = combine_with_and(
        [
            ContentPredicate("alpha"),
            ContentPredicate("bravo"),
        ]
    )

    session = search_with_stats(tmp_path, predicate)
    content_lines = [result.line_text for result in session.results if result.match_kind == "content"]

    assert content_lines == ["alpha and bravo"]


def test_and_multiple_contains_falls_back_to_path_when_no_shared_line(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\nbravo\n", encoding="utf-8")
    predicate = combine_with_and(
        [
            ContentPredicate("alpha"),
            ContentPredicate("bravo"),
        ]
    )

    session = search_with_stats(tmp_path, predicate)
    results = list(session.results)

    assert len(results) == 1
    assert results[0].match_kind == "path"


def test_three_contains_and_requires_shared_line(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha beta\nalpha beta gamma\n", encoding="utf-8")
    predicate = combine_with_and(
        [
            ContentPredicate("alpha"),
            ContentPredicate("beta"),
            ContentPredicate("gamma"),
        ]
    )

    session = search_with_stats(tmp_path, predicate)
    content_lines = [result.line_text for result in session.results if result.match_kind == "content"]

    assert content_lines == ["alpha beta gamma"]


def test_not_contains_with_name_filter(tmp_path: Path):
    clean = tmp_path / "clean.py"
    flagged = tmp_path / "flagged.py"
    clean.write_text("ok\n", encoding="utf-8")
    flagged.write_text("TODO\n", encoding="utf-8")
    predicate = compile_ast(parse_query("name:*.py AND NOT contains:TODO"))

    session = search_with_stats(tmp_path, predicate)
    matched = {result.relative_path.name for result in session.results}

    assert matched == {"clean.py"}


def test_limit_counts_files_not_content_lines(tmp_path: Path):
    (tmp_path / "one.txt").write_text("TODO\nTODO\nTODO\n", encoding="utf-8")
    (tmp_path / "two.txt").write_text("TODO\n", encoding="utf-8")

    session = search_with_stats(
        tmp_path,
        ContentPredicate("TODO"),
        SearchOptions(limit=1),
    )
    results = list(session.results)

    assert session.stats.files_matched == 1
    assert session.stats.stopped_early is True
    assert len({result.relative_path.as_posix() for result in results}) == 1
    assert len(results) == 3


def test_sort_limit_summary_reflects_output(tmp_path: Path):
    (tmp_path / "a.txt").write_text("TODO\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("TODO\n", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args([str(tmp_path), "--contains", "TODO", "--sort", "name", "--limit", "1", "--summary"])
    stdout = StringIO()
    stderr = StringIO()
    code = run(args, stdout=stdout, stderr=stderr)

    assert code == 0
    assert "matched_files=1" in stderr.getvalue()
    assert "stopped early" in stderr.getvalue()
    assert "a.txt" in stdout.getvalue()
    assert "b.txt" not in stdout.getvalue()


def test_examples_query_line_four(tmp_path: Path):
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    old = datetime.now(timezone.utc) - timedelta(days=30)
    recent_path = tmp_path / "recent.py"
    old_path = tmp_path / "archive.md"
    recent_path.write_text("", encoding="utf-8")
    old_path.write_text("", encoding="utf-8")
    recent_ts = recent.timestamp()
    old_ts = old.timestamp()
    os.utime(recent_path, (recent_ts, recent_ts))
    os.utime(old_path, (old_ts, old_ts))

    predicate = compile_ast(parse_query("(ext:py OR ext:md) AND modified:within:7d"))
    session = search_with_stats(tmp_path, predicate)
    matched = {result.relative_path.name for result in session.results}

    assert matched == {"recent.py"}


def test_dsl_ext_strips_whitespace(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")
    predicate = compile_ast(parse_query("ext:py, md"))

    assert predicate.matches(make_entry(path, tmp_path))


def test_query_and_cli_flags_are_anded(tmp_path: Path):
    (tmp_path / "app.py").write_text("TODO\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("TODO\n", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args([str(tmp_path), "--query", "contains:TODO", "--ext", "py"])
    search_options, _ = options_from_namespace(args)
    predicate = predicate_from_namespace(args, search_options)

    session = search_with_stats(tmp_path, predicate)
    matched = [result.relative_path.as_posix() for result in session.results]

    assert matched == ["app.py"]


def test_conflicting_case_flags_raise_cli_error():
    parser = build_parser()
    args = parser.parse_args([".", "--ignore-case", "--case-sensitive"])

    with pytest.raises(CLIError, match="cannot use --ignore-case and --case-sensitive together"):
        options_from_namespace(args)


def test_exclude_respects_ignore_case(tmp_path: Path):
    target = tmp_path / "SkipMe.txt"
    target.write_text("x", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")

    session = search_with_stats(
        tmp_path,
        ContentPredicate("x"),
        SearchOptions(exclude_patterns=["SKIPME.*"], case_sensitive=False),
    )
    matched = {result.relative_path.name for result in session.results}

    assert "keep.txt" in matched
    assert "SkipMe.txt" not in matched
    assert session.stats.entries_skipped >= 1


@pytest.mark.skipif(sys.platform == "win32", reason="directory symlinks require elevated privileges on Windows")
def test_symlink_cycle_is_not_yielded_twice(tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "to_right").symlink_to(right, target_is_directory=True)
    (right / "to_left").symlink_to(left, target_is_directory=True)
    (left / "note.txt").write_text("x", encoding="utf-8")

    entries = list(walk(left, SearchOptions(follow_symlinks=True), SearchStats()))
    resolved_paths = [entry.path.resolve() for entry in entries]

    assert len(resolved_paths) == len(set(resolved_paths))


def test_verbose_reports_binary_skip(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"TODO\x00")
    parser = build_parser()
    args = parser.parse_args([str(tmp_path), "--contains", "TODO", "--verbose"])
    stderr = StringIO()
    run(args, stderr=stderr, stdout=StringIO())

    assert "binary file skipped" in stderr.getvalue()


def test_tree_formatter_renders_content_lines(tmp_path: Path):
    root = tmp_path / "src"
    root.mkdir()
    path = root / "app.py"
    path.write_text("TODO\n", encoding="utf-8")
    result = SearchResult(
        path=path,
        relative_path=Path("src/app.py"),
        type="file",
        size=4,
        mtime=1.0,
        match_kind="content",
        line_number=1,
        line_text="TODO",
        matched_text="TODO",
    )

    output = tree_formatter.format_results([result])

    assert "app.py:1: TODO" in output


def test_sync_stats_for_output_updates_summary_counts():
    results = [
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "content", 1, "x", "x"),
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "content", 2, "y", "y"),
        SearchResult(Path("b"), Path("b"), "file", 1, 1.0, "path"),
    ]
    stats = SearchStats(files_matched=5, content_matches=9)

    sync_stats_for_output(stats, results, limit_applied=True)

    assert stats.files_matched == 2
    assert stats.content_matches == 2
    assert stats.stopped_early is True


def test_and_or_contains_emits_shared_line(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha beta\nalpha only\nbeta only\n", encoding="utf-8")
    predicate = compile_ast(parse_query("contains:alpha AND (contains:beta OR contains:gamma)"))

    session = search_with_stats(tmp_path, predicate)
    content_lines = [result.line_text for result in session.results if result.match_kind == "content"]

    assert content_lines == ["alpha beta"]


def test_content_ignore_case_flag(tmp_path: Path):
    path = tmp_path / "Notes.txt"
    path.write_text("todo item\n", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args([str(tmp_path), "--contains", "TODO", "--content-ignore-case"])

    session = search_with_stats(tmp_path, predicate_from_namespace(args, options_from_namespace(args)[0]))
    results = list(session.results)

    assert any(result.match_kind == "content" for result in results)
