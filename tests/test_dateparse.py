"""Test date and duration parsing."""

from datetime import datetime, timedelta, timezone

import pytest

from file_search_tool.dateparse import (
    duration_to_timedelta,
    local_midnight_timestamp,
    modified_after,
    modified_before,
    modified_within,
    parse_modified_expression,
)
from file_search_tool.errors import InvalidDateExpression


def test_duration_parsing():
    assert duration_to_timedelta("3h") == timedelta(hours=3)
    assert duration_to_timedelta("2w") == timedelta(weeks=2)


def test_empty_date_and_duration_expressions_are_rejected():
    with pytest.raises(InvalidDateExpression, match="empty date expression"):
        local_midnight_timestamp("")
    with pytest.raises(InvalidDateExpression, match="empty duration expression"):
        duration_to_timedelta("")


def test_modified_within_matches_recent_timestamp():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    rule = modified_within("7d", now=now)

    assert rule.matches((now - timedelta(days=1)).timestamp())
    assert not rule.matches((now - timedelta(days=8)).timestamp())


def test_parse_modified_expression_requires_prefix():
    with pytest.raises(InvalidDateExpression):
        parse_modified_expression("7d")


def test_modified_before_and_after_boundaries():
    midnight = local_midnight_timestamp("2026-01-15")

    assert modified_before("2026-01-15").matches(midnight - 1)
    assert not modified_before("2026-01-15").matches(midnight)
    assert modified_after("2026-01-15").matches(midnight)
    assert not modified_after("2026-01-15").matches(midnight - 1)


def test_modified_within_excludes_boundary_timestamp():
    now = datetime(2026, 5, 26, 12, tzinfo=timezone.utc)
    rule = modified_within("1d", now=now)

    assert rule.matches((now - timedelta(hours=1)).timestamp())
    assert not rule.matches((now - timedelta(days=1)).timestamp())


def test_parse_modified_expression_supports_dsl_prefixes():
    rule = parse_modified_expression("within:7d")

    assert rule.operator == "within"


def test_duration_invalid_unit_via_monkeypatch(monkeypatch):
    import file_search_tool.dateparse as dateparse_module

    class FakeMatch:
        def group(self, name: str):
            if name == "number":
                return "1"
            if name == "unit":
                return "x"
            raise KeyError(name)

    monkeypatch.setattr(dateparse_module, "DURATION_RE", type("R", (), {"match": lambda self, _: FakeMatch()})())

    with pytest.raises(InvalidDateExpression, match="invalid duration unit"):
        duration_to_timedelta("1x")


def test_invalid_date_and_duration_raise():
    with pytest.raises(InvalidDateExpression, match="invalid date"):
        local_midnight_timestamp("not-a-date")
    with pytest.raises(InvalidDateExpression, match="invalid duration"):
        duration_to_timedelta("3m")


def test_modified_time_filter_rejects_none_mtime():
    rule = modified_before("2026-01-01")

    assert not rule.matches(None)


def test_modified_time_filter_rejects_unknown_operator():
    from file_search_tool.dateparse import ModifiedTimeFilter

    rule = ModifiedTimeFilter("bogus", 0.0)

    with pytest.raises(InvalidDateExpression, match="unknown modified-time operator"):
        rule.matches(1.0)


def test_parse_modified_expression_supports_before_and_after():
    before_rule = parse_modified_expression("before:2026-01-01")
    after_rule = parse_modified_expression("after:2026-01-01")

    assert before_rule.operator == "before"
    assert after_rule.operator == "after"

