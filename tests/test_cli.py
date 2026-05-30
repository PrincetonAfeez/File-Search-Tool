"""Test the file search tool CLI."""

from io import StringIO
from pathlib import Path
import os
import runpy
import sys

import pytest

from file_search_tool.cli import _apply_file_limit, build_parser, main, run
from file_search_tool.models import SearchResult


def invoke(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    stdout = StringIO()
    stderr = StringIO()
    code = run(args, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_cli_basic_name_search(tmp_path: Path):
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.py"])

    assert code == 0
    assert "app.py" in stdout
    assert "README.md" not in stdout


def test_cli_no_matches_returns_one(tmp_path: Path):
    (tmp_path / "README.md").write_text("", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.py"])

    assert code == 1
    assert stdout == ""


def test_cli_contains_outputs_line_number(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("TODO now\n", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--contains", "TODO"])

    assert code == 0
    assert "notes.txt:1: TODO now" in stdout


def test_cli_json_output(tmp_path: Path):
    (tmp_path / "app.py").write_text("", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.py", "--format", "json"])

    assert code == 0
    assert '"relative_path": "app.py"' in stdout


def test_cli_limit_stops_early_and_summary_says_so(tmp_path: Path):
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")

    code, stdout, stderr = invoke([str(tmp_path), "--name", "*.txt", "--limit", "1", "--summary"])

    assert code == 0
    assert stdout.count("a.txt") + stdout.count("b.txt") == 1
    assert "matched_files=1" in stderr
    assert "stopped early" in stderr


def test_cli_limit_with_content_counts_files_not_lines(tmp_path: Path):
    (tmp_path / "one.txt").write_text("TODO\nTODO\n", encoding="utf-8")
    (tmp_path / "two.txt").write_text("TODO\n", encoding="utf-8")

    code, stdout, stderr = invoke([str(tmp_path), "--contains", "TODO", "--limit", "1", "--summary"])

    assert code == 0
    assert "one.txt" in stdout
    assert "two.txt" not in stdout
    assert "matched_files=1" in stderr


def test_cli_summary_reports_entries_skipped(tmp_path: Path):
    (tmp_path / "keep.txt").write_text("", encoding="utf-8")
    skipped = tmp_path / "SkipMe.txt"
    skipped.write_text("", encoding="utf-8")

    code, stdout, stderr = invoke(
        [
            str(tmp_path),
            "--name",
            "*.txt",
            "--exclude",
            "SKIPME.*",
            "--ignore-case",
            "--summary",
        ]
    )

    assert code == 0
    assert "entries_skipped=" in stderr


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["--limit", "0", "--name", "*.py"], "--limit must be greater than 0"),
        (["--depth", "-1", "--name", "*.py"], "--depth must be 0 or greater"),
        (["--size", "+10XB", "--name", "*.py"], "invalid size"),
        (["--query", "name:"], "missing value for field 'name'"),
        (["--ext", ",,"], "extension list cannot be empty"),
        (["--query", "ext:,,"], "extension list cannot be empty"),
        (["--name", ""], "name pattern cannot be empty"),
        (["--path", ""], "path pattern cannot be empty"),
        (["--regex-name", ""], "name pattern cannot be empty"),
        (["--contains-regex", ""], "content search pattern cannot be empty"),
        (["--size", ""], "empty size expression"),
        (["--modified-before", ""], "empty date expression"),
        (["--modified-after", ""], "empty date expression"),
        (["--modified-within", ""], "empty duration expression"),
        (["--exclude", ""], "--exclude pattern cannot be empty"),
    ],
)
def test_cli_exit_code_two_for_expected_errors(tmp_path: Path, monkeypatch, argv, expected):
    stderr = StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)
    code = main([str(tmp_path), *argv])

    assert code == 2
    assert expected in stderr.getvalue()


def test_cli_missing_root_returns_three(monkeypatch):
    stderr = StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)
    code = main(["/no/such/root/for/file-search", "--name", "*.py"])

    assert code == 3
    assert "root path does not exist" in stderr.getvalue()


def test_cli_query_error_prefix(tmp_path: Path, monkeypatch):
    stderr = StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)
    code = main([str(tmp_path), "--query", "name:"])

    assert code == 2
    assert stderr.getvalue().startswith("query error:")


def test_cli_binary_error_flag(tmp_path: Path, monkeypatch):
    path = tmp_path / "data.bin"
    path.write_bytes(b"TODO\x00")
    stderr = StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)
    code = main([str(tmp_path), "--contains", "TODO", "--binary-error"])

    assert code == 3
    assert "binary file not searchable" in stderr.getvalue()


def test_run_returns_two_for_invalid_limit(tmp_path: Path):
    code, _, stderr = invoke([str(tmp_path), "--limit", "0", "--name", "*.py"])

    assert code == 2
    assert "--limit must be greater than 0" in stderr


def test_binary_error_buffers_plain_output(tmp_path: Path):
    (tmp_path / "a.bin").write_bytes(b"\x00")
    (tmp_path / "b.txt").write_text("TODO\n", encoding="utf-8")

    code, stdout, stderr = invoke([str(tmp_path), "--contains", "TODO", "--binary-error"])

    assert code == 3
    assert stdout == ""
    assert "binary file not searchable" in stderr


def test_cli_empty_contains_is_rejected(tmp_path: Path):
    (tmp_path / "a.txt").write_text("anything\n", encoding="utf-8")

    code, _, stderr = invoke([str(tmp_path), "--contains", ""])

    assert code == 2
    assert "content search pattern cannot be empty" in stderr


def test_cli_dsl_size_error_uses_query_prefix(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    code, _, stderr = invoke([str(tmp_path), "--query", "size:bad"])

    assert code == 2
    assert stderr.startswith("query error:")


def test_cli_dsl_modified_error_uses_query_prefix(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    code, _, stderr = invoke([str(tmp_path), "--query", "modified:nonsense"])

    assert code == 2
    assert stderr.startswith("query error:")


def test_summary_plain_limit_reports_partial_scan(tmp_path: Path):
    for index in range(5):
        (tmp_path / f"f{index}.txt").write_text("", encoding="utf-8")

    code, stdout, stderr = invoke([str(tmp_path), "--name", "*.txt", "--limit", "2", "--summary"])

    assert code == 0
    assert "matched_files=2" in stderr
    assert "files=2" in stderr
    assert "stopped early" in stderr


def test_summary_sorted_limit_reports_full_scan(tmp_path: Path):
    for index in range(5):
        (tmp_path / f"f{index}.txt").write_text("", encoding="utf-8")

    code, stdout, stderr = invoke(
        [str(tmp_path), "--name", "*.txt", "--limit", "2", "--sort", "name", "--summary"]
    )

    assert code == 0
    assert "matched_files=2" in stderr
    assert "files=5" in stderr
    assert "stopped early" in stderr


def test_main_module_entrypoint_runs(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["file-search", str(tmp_path), "--name", "*.py"])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("file_search_tool", run_name="__main__")

    assert excinfo.value.code == 0
    assert "app.py" in capsys.readouterr().out


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "file-search" in output


def test_cli_tree_output(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.py", "--format", "tree"])

    assert code == 0
    assert "src/" in stdout
    assert "app.py" in stdout


def test_cli_sort_by_size_and_mtime(tmp_path: Path):
    small = tmp_path / "small.txt"
    large = tmp_path / "large.txt"
    small.write_text("a", encoding="utf-8")
    large.write_text("a" * 20, encoding="utf-8")
    os.utime(small, (100.0, 100.0))
    os.utime(large, (200.0, 200.0))

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.txt", "--sort", "size"])

    assert code == 0
    assert stdout.index("small.txt") < stdout.index("large.txt")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.txt", "--sort", "mtime"])

    assert code == 0
    assert stdout.index("small.txt") < stdout.index("large.txt")


def test_apply_file_limit_keeps_all_content_lines_for_first_files():
    results = [
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "content", 1, "x", "x"),
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "content", 2, "y", "y"),
        SearchResult(Path("b"), Path("b"), "file", 1, 1.0, "path"),
    ]

    limited = _apply_file_limit(results, 1)

    assert len(limited) == 2
    assert all(result.relative_path.as_posix() == "a" for result in limited)


def test_cli_plain_sort_by_name(tmp_path: Path):
    (tmp_path / "b.txt").write_text("", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")

    code, stdout, _ = invoke([str(tmp_path), "--name", "*.txt", "--sort", "name"])

    assert code == 0
    assert stdout.splitlines() == ["a.txt", "b.txt"]


def test_cli_verbose_prints_warnings(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"TODO\x00")

    code, _, stderr = invoke([str(tmp_path), "--contains", "TODO", "--verbose"])

    assert code == 1
    assert "binary file skipped" in stderr


def test_package_version_falls_back_when_missing(monkeypatch):
    from importlib.metadata import PackageNotFoundError

    from file_search_tool import cli as cli_module

    def raise_not_found(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(cli_module, "version", raise_not_found)

    assert cli_module._package_version() == "unknown"
