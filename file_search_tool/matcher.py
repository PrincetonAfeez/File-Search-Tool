"""Matching helpers for glob and regex patterns."""

from __future__ import annotations

from fnmatch import fnmatchcase
import re
from re import Pattern

from file_search_tool.errors import InvalidFilterError


def glob_matches(value: str, pattern: str, case_sensitive: bool = True) -> bool:
    if case_sensitive:
        return fnmatchcase(value, pattern)
    return fnmatchcase(value.casefold(), pattern.casefold())


def compile_regex(pattern: str, case_sensitive: bool = True) -> Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise InvalidFilterError(f"invalid regex: {pattern}") from exc

