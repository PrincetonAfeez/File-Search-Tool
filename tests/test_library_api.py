"""Test the library API."""

import file_search_tool
from file_search_tool.errors import (
    CLIError,
    ContentSearchError,
    FileSearchError,
    InvalidDateExpression,
    InvalidFilterError,
    InvalidSizeExpression,
    QuerySyntaxError,
    TraversalError,
)


def test_public_package_exports():
    assert set(file_search_tool.__all__) == {
        "FileEntry",
        "SearchOptions",
        "SearchResult",
        "SearchSession",
        "SearchStats",
        "search",
        "search_with_stats",
    }


def test_error_hierarchy():
    assert issubclass(TraversalError, FileSearchError)
    assert issubclass(QuerySyntaxError, FileSearchError)
    assert issubclass(InvalidSizeExpression, FileSearchError)
    assert issubclass(InvalidDateExpression, FileSearchError)
    assert issubclass(InvalidFilterError, FileSearchError)
    assert issubclass(ContentSearchError, FileSearchError)
    assert issubclass(CLIError, FileSearchError)
