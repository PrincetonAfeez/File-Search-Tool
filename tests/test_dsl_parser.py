"""Test the DSL parser."""

import pytest

from file_search_tool.dsl.ast import AndNode, FilterNode, NotNode, OrNode
from file_search_tool.dsl.parser import parse_query
from file_search_tool.errors import QuerySyntaxError


def test_parser_parses_filter():
    node = parse_query("name:*.py")

    assert node == FilterNode("name", "*.py")


def test_parser_precedence_not_and_or():
    node = parse_query("name:*.py OR NOT ext:md AND path:src/*")

    assert isinstance(node, OrNode)
    assert isinstance(node.right, AndNode)
    assert isinstance(node.right.left, NotNode)


def test_parser_reports_missing_value():
    with pytest.raises(QuerySyntaxError):
        parse_query("name:")


def test_parser_reports_empty_query():
    with pytest.raises(QuerySyntaxError, match="empty query"):
        parse_query("")


def test_parser_reports_unclosed_group():
    with pytest.raises(QuerySyntaxError):
        parse_query("(name:*.py")
    with pytest.raises(QuerySyntaxError, match="unexpected token"):
        parse_query("(name:*.py) extra")


def test_parser_requires_connective_before_adjacent_filter():
    with pytest.raises(QuerySyntaxError, match="expected AND/OR before 'contains'"):
        parse_query("name:*.py contains:TODO")

    node = parse_query("name:*.py AND contains:TODO")
    assert node == AndNode(FilterNode("name", "*.py"), FilterNode("contains", "TODO"))


def test_parser_rejects_glued_filters_without_whitespace():
    with pytest.raises(QuerySyntaxError, match="expected AND/OR before 'contains'"):
        parse_query("name:*.pyNOTcontains:TODO")


def test_parser_reports_adjacent_expressions_at_top_level():
    with pytest.raises(QuerySyntaxError, match="expected AND/OR"):
        parse_query("(name:foo) NOT bar:baz")

