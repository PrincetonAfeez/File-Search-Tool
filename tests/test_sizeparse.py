"""Test the size parsing."""

import pytest

from file_search_tool.errors import InvalidSizeExpression
from file_search_tool.sizeparse import parse_size_expression, parse_size_value


def test_parse_binary_units():
    assert parse_size_value("1KB") == 1024
    assert parse_size_value("2MB") == 2 * 1024 * 1024


def test_parse_greater_than_expression():
    rule = parse_size_expression("+10B")

    assert rule.matches(11)
    assert not rule.matches(10)


def test_parse_range_expression():
    rule = parse_size_expression("1KB..2KB")

    assert rule.matches(1024)
    assert rule.matches(2048)
    assert not rule.matches(2049)


def test_invalid_size_expression_raises():
    with pytest.raises(InvalidSizeExpression):
        parse_size_expression("10XB")


def test_parse_exact_size_expression():
    rule = parse_size_expression("1024")

    assert rule.operator == "eq"
    assert rule.matches(1024)
    assert not rule.matches(1025)


def test_parse_comparison_operators():
    assert parse_size_expression("<=1KB").matches(1024)
    assert not parse_size_expression("<=1KB").matches(1025)
    assert parse_size_expression(">=512B").matches(512)
    assert parse_size_expression("-1KB").matches(512)
    assert not parse_size_expression("-1KB").matches(2048)


def test_parse_size_rejects_empty_or_incomplete_expressions():
    with pytest.raises(InvalidSizeExpression, match="empty size expression"):
        parse_size_expression("")
    with pytest.raises(InvalidSizeExpression, match="missing size value"):
        parse_size_expression("+")
    with pytest.raises(InvalidSizeExpression, match="invalid size range"):
        parse_size_expression("5KB..1KB")
    with pytest.raises(InvalidSizeExpression, match="invalid size range"):
        parse_size_expression("..5KB")


def test_size_filter_rejects_none_size():
    rule = parse_size_expression("+1B")

    assert not rule.matches(None)


def test_size_filter_rejects_unknown_operator():
    from file_search_tool.sizeparse import SizeFilter

    rule = SizeFilter("bogus", 1)

    with pytest.raises(InvalidSizeExpression, match="unknown size operator"):
        rule.matches(10)


def test_parse_size_value_rejects_invalid_unit(monkeypatch):
    import file_search_tool.sizeparse as sizeparse_module

    monkeypatch.setattr(sizeparse_module, "UNITS", {"B": 1})

    with pytest.raises(InvalidSizeExpression, match="invalid size unit"):
        parse_size_value("1KB")

