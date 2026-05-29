"""Regression tests for Medium/Low correctness fixes (T1–T6)."""

from __future__ import annotations

import json
from io import StringIO

import pytest

from file_search_tool.cli import build_parser, run
from file_search_tool.dsl import compile_ast, parse_query
from file_search_tool.errors import QuerySyntaxError
from file_search_tool.search import search_with_stats


def invoke(argv: list[str]):
    parser = build_parser()
    args = parser.parse_args(argv)
    stdout = StringIO()
    stderr = StringIO()
    code = run(args, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_t1_limit_above_matches_no_stopped_early_in_sorted_mode(tmp_path):
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")

    code, _, stderr = invoke(
        [str(tmp_path), "--name", "*.txt", "--limit", "100", "--sort", "name", "--summary"]
    )

    assert code == 0
    assert "matched_files=2" in stderr
    assert "stopped early" not in stderr


def test_t2_json_summary_stdout_is_valid_json(tmp_path):
    (tmp_path / "app.py").write_text("", encoding="utf-8")

    code, stdout, stderr = invoke([str(tmp_path), "--name", "*.py", "--format", "json", "--summary"])

    assert code == 0
    json.loads(stdout)
    assert "summary:" in stderr


def test_t3_missing_operator_before_not_raises_query_syntax_error():
    with pytest.raises(QuerySyntaxError):
        parse_query("name:*.py NOT contains:TODO")


def test_t4_or_contains_on_same_line_emits_one_search_result(tmp_path):
    (tmp_path / "notes.txt").write_text("alpha bravo\n", encoding="utf-8")
    predicate = compile_ast(parse_query("contains:alpha OR contains:bravo"))

    session = search_with_stats(tmp_path, predicate)
    content_results = [result for result in session.results if result.match_kind == "content"]

    assert len(content_results) == 1


def test_t5_case_insensitive_contains_preserves_original_matched_text(tmp_path):
    (tmp_path / "gross.txt").write_text("gro\u00df stuff\n", encoding="utf-8")

    code, stdout, stderr = invoke(
        [str(tmp_path), "--contains", "gross", "--content-ignore-case"]
    )

    assert code == 0
    assert stderr == ""
    assert stdout == "gross.txt:1: gro\u00df stuff\n"


@pytest.mark.parametrize(
    "flag,message",
    [
        ("--query", "empty query"),
        ("--name", "name pattern cannot be empty"),
        ("--regex-name", "name pattern cannot be empty"),
        ("--path", "path pattern cannot be empty"),
        ("--contains-regex", "content search pattern cannot be empty"),
        ("--size", "empty size expression"),
    ],
)
def test_t6_empty_cli_flags_exit_two_with_clear_message(tmp_path, flag, message):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    code, _, stderr = invoke([str(tmp_path), flag, ""])

    assert code == 2
    assert message in stderr


@pytest.mark.parametrize(
    "flag,message",
    [
        ("--modified-before", "empty date expression"),
        ("--modified-after", "empty date expression"),
        ("--modified-within", "empty duration expression"),
    ],
)
def test_empty_modified_flags_exit_two_with_clear_message(tmp_path, flag, message):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    code, _, stderr = invoke([str(tmp_path), flag, ""])

    assert code == 2
    assert message in stderr
