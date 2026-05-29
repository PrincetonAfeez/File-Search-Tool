"""Test the matcher."""

import pytest

from file_search_tool.errors import InvalidFilterError
from file_search_tool.matcher import compile_regex, glob_matches


def test_glob_matches_case_insensitive():
    assert glob_matches("README.MD", "*.md", case_sensitive=False)


def test_invalid_regex_raises_filter_error():
    with pytest.raises(InvalidFilterError):
        compile_regex("[")

