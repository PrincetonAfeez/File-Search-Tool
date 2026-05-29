"""Test the DSL predicates."""

from pathlib import Path

import pytest

from file_search_tool.dsl import compile_ast, parse_query
from file_search_tool.errors import QuerySyntaxError
from file_search_tool.models import FileEntry


def make_entry(path: Path, root: Path):
    return FileEntry(path, root, path.relative_to(root), True, False, False, path.stat().st_size, path.stat().st_mtime, 1)


def test_dsl_compiles_and_predicate(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("TODO\n", encoding="utf-8")
    predicate = compile_ast(parse_query("name:*.py AND contains:TODO"))

    assert predicate.matches(make_entry(path, tmp_path))


def test_dsl_compiles_not_predicate(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")
    predicate = compile_ast(parse_query("name:*.py AND NOT path:tests/*"))

    assert predicate.matches(make_entry(path, tmp_path))


def test_dsl_unknown_field_raises_query_error():
    with pytest.raises(QuerySyntaxError, match="unknown field"):
        compile_ast(parse_query("unknown:value"))


def test_compile_ast_rejects_unsupported_node():
    with pytest.raises(QuerySyntaxError, match="unsupported query node"):
        compile_ast(object())


def test_dsl_compiles_type_file(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")
    predicate = compile_ast(parse_query("type:file"))

    assert predicate.matches(make_entry(path, tmp_path))


def test_dsl_unknown_type_raises_query_error():
    with pytest.raises(QuerySyntaxError, match="unknown type"):
        compile_ast(parse_query("type:executable"))

