"""Test helpers for the file search tool CLI."""

from io import StringIO
from pathlib import Path

import pytest

from file_search_tool.cli import (
    _needs_deferred_limit,
    _print_warnings,
    _should_buffer_plain_output,
    _sort_results,
    build_parser,
    run,
)
from file_search_tool.models import CliDisplayOptions, SearchOptions, SearchResult
from file_search_tool.search import count_unique_matched_files


def invoke(argv: list[str]):
    parser = build_parser()
    args = parser.parse_args(argv)
    stdout = StringIO()
    stderr = StringIO()
    code = run(args, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_sort_results_passthrough_when_sort_is_none():
    results = [
        SearchResult(Path("b"), Path("b"), "file", 1, 1.0, "path"),
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "path"),
    ]

    assert _sort_results(results, None) == results


def test_sort_results_puts_entries_without_size_or_mtime_last():
    results = [
        SearchResult(Path("dir"), Path("dir"), "dir", None, None, "path"),
        SearchResult(Path("small.txt"), Path("small.txt"), "file", 1, 100.0, "path"),
        SearchResult(Path("large.txt"), Path("large.txt"), "file", 100, 50.0, "path"),
    ]

    by_size = _sort_results(results, "size")
    assert [item.relative_path.name for item in by_size] == ["small.txt", "large.txt", "dir"]

    by_mtime = _sort_results(results, "mtime")
    assert [item.relative_path.name for item in by_mtime] == ["large.txt", "small.txt", "dir"]


def test_needs_deferred_limit_only_for_sort_or_non_plain_formats():
    display = CliDisplayOptions()

    assert _needs_deferred_limit(display, 5) is False
    assert _needs_deferred_limit(CliDisplayOptions(sort_by="name"), 5) is True
    assert _needs_deferred_limit(CliDisplayOptions(output_format="json"), 5) is True
    assert _needs_deferred_limit(CliDisplayOptions(output_format="tree"), 5) is True


def test_should_buffer_plain_output_when_binary_error_enabled():
    assert _should_buffer_plain_output(SearchOptions(binary_policy="error")) is True
    assert _should_buffer_plain_output(SearchOptions(binary_policy="skip")) is False


def test_print_warnings_writes_to_stderr():
    stderr = StringIO()

    _print_warnings(["first", "second"], stderr)

    output = stderr.getvalue()
    assert "warning: first" in output
    assert "warning: second" in output


def test_count_matched_files_counts_unique_paths():
    results = [
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "content", 1, "x", "x"),
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "content", 2, "y", "y"),
        SearchResult(Path("b"), Path("b"), "file", 1, 1.0, "path"),
    ]

    assert count_unique_matched_files(results) == 2


def test_binary_error_buffers_and_prints_text_matches(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("TODO\n", encoding="utf-8")

    code, stdout, stderr = invoke([str(tmp_path), "--contains", "TODO", "--binary-error"])

    assert code == 0
    assert "TODO" in stdout
    assert stderr == ""


def test_tree_format_with_no_matches_prints_nothing(tmp_path: Path):
    (tmp_path / "keep.txt").write_text("", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.missing", "--format", "tree"])

    assert code == 1
    assert stdout == ""


def test_run_returns_two_for_traversal_error(tmp_path: Path):
    code, _, stderr = invoke([str(tmp_path / "missing"), "--name", "*.txt"])

    assert code == 2
    assert "root path does not exist" in stderr


def test_build_parser_exposes_all_documented_flags():
    parser = build_parser()
    names = {action.dest for action in parser._actions if action.dest != "help"}

    expected = {
        "root",
        "version",
        "name",
        "regex_name",
        "path_pattern",
        "ext",
        "entry_type",
        "size",
        "modified_before",
        "modified_after",
        "modified_within",
        "contains",
        "contains_regex",
        "query",
        "depth",
        "exclude",
        "include_hidden",
        "follow_symlinks",
        "ignore_case",
        "case_sensitive",
        "content_ignore_case",
        "binary_error",
        "limit",
        "sort",
        "output_format",
        "summary",
        "verbose",
    }
    assert expected.issubset(names)


def test_cli_direct_main_guard_executes(tmp_path: Path, monkeypatch):
    from runpy import run_path

    (tmp_path / "solo.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["file-search", str(tmp_path), "--name", "*.txt"])

    with pytest.raises(SystemExit) as excinfo:
        run_path(
            str(Path(__file__).resolve().parents[1] / "file_search_tool" / "cli.py"),
            run_name="__main__",
        )

    assert excinfo.value.code in {0, 1}
