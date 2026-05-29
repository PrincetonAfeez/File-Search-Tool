"""Composable search predicates."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from file_search_tool.content import (
    ContentMatch,
    ContentReadCache,
    compile_content_regex,
    find_content_matches,
)
from file_search_tool.dateparse import ModifiedTimeFilter
from file_search_tool.errors import ContentSearchError, InvalidFilterError
from file_search_tool.matcher import compile_regex, glob_matches
from file_search_tool.models import FileEntry, SearchStats
from file_search_tool.sizeparse import SizeFilter
from file_search_tool.utils import normalize_relative_path


class Predicate(Protocol):
    """The interface the search engine relies on for any predicate tree."""

    def matches(self, entry: FileEntry) -> bool:
        ...

    def bind_stats(self, stats: SearchStats, warnings: list[str] | None = None) -> None:
        ...

    def bind_read_cache(self, cache: ContentReadCache) -> None:
        ...

    def collect_content_matches(self, entry: FileEntry) -> list[ContentMatch]:
        ...

    def clear_entry_caches(self) -> None:
        ...


def _intersect_content_match_lists(groups: list[list[ContentMatch]]) -> list[ContentMatch]:
    if not groups:
        return []
    common_lines = set(match.line_number for match in groups[0])
    for group in groups[1:]:
        common_lines &= {match.line_number for match in group}
    if not common_lines:
        return []
    first_by_line = {match.line_number: match for match in groups[0]}
    return [first_by_line[line_number] for line_number in sorted(common_lines)]


class BasePredicate:
    def matches(self, entry: FileEntry) -> bool:
        raise NotImplementedError

    def bind_stats(self, stats: SearchStats, warnings: list[str] | None = None) -> None:
        return None

    def bind_read_cache(self, cache: ContentReadCache) -> None:
        return None

    def collect_content_matches(self, entry: FileEntry) -> list[ContentMatch]:
        return []

    def clear_entry_caches(self) -> None:
        return None


@dataclass
class NamePredicate(BasePredicate):
    pattern: str
    regex: bool = False
    case_sensitive: bool = True

    def __post_init__(self) -> None:
        if not self.pattern:
            raise InvalidFilterError("name pattern cannot be empty")
        self._regex = compile_regex(self.pattern, self.case_sensitive) if self.regex else None

    def matches(self, entry: FileEntry) -> bool:
        if self._regex is not None:
            return self._regex.search(entry.path.name) is not None
        return glob_matches(entry.path.name, self.pattern, self.case_sensitive)


@dataclass
class PathPredicate(BasePredicate):
    pattern: str
    regex: bool = False
    case_sensitive: bool = True

    def __post_init__(self) -> None:
        if not self.pattern:
            raise InvalidFilterError("path pattern cannot be empty")
        self._regex = compile_regex(self.pattern, self.case_sensitive) if self.regex else None

    def matches(self, entry: FileEntry) -> bool:
        value = normalize_relative_path(entry.relative_path)
        if self._regex is not None:
            return self._regex.search(value) is not None
        return glob_matches(value, self.pattern, self.case_sensitive)


@dataclass
class ExtensionPredicate(BasePredicate):
    extensions: list[str]
    case_sensitive: bool = True

    def __post_init__(self) -> None:
        normalized: list[str] = []
        for ext in self.extensions:
            clean = ext.strip()
            if not clean:
                continue
            if not clean.startswith("."):
                clean = f".{clean}"
            if not any(character.isalnum() for character in clean.lstrip(".")):
                continue
            normalized.append(clean if self.case_sensitive else clean.casefold())
        if not normalized:
            raise InvalidFilterError("extension list cannot be empty")
        self._extensions = set(normalized)

    def matches(self, entry: FileEntry) -> bool:
        suffix = entry.path.suffix if self.case_sensitive else entry.path.suffix.casefold()
        return suffix in self._extensions


@dataclass
class TypePredicate(BasePredicate):
    expected_type: str

    def matches(self, entry: FileEntry) -> bool:
        if self.expected_type == "symlink":
            return entry.is_symlink
        if self.expected_type == "dir":
            return entry.is_dir and not entry.is_symlink
        if self.expected_type == "file":
            return entry.is_file and not entry.is_symlink
        return False


@dataclass
class SizePredicate(BasePredicate):
    size_filter: SizeFilter

    def matches(self, entry: FileEntry) -> bool:
        return self.size_filter.matches(entry.size)


@dataclass
class ModifiedTimePredicate(BasePredicate):
    modified_filter: ModifiedTimeFilter

    def matches(self, entry: FileEntry) -> bool:
        return self.modified_filter.matches(entry.mtime)


def _record_binary_skip(path: Path, stats: SearchStats | None, warnings: list[str] | None) -> None:
    if stats is None:
        return
    if stats.record_binary_skip(path) and warnings is not None:
        warnings.append(f"binary file skipped: {path}")


def _record_content_access_error(path: Path, stats: SearchStats | None, warnings: list[str] | None) -> None:
    if stats is not None:
        stats.permission_errors += 1
    if warnings is not None:
        warnings.append(f"cannot read file for content search: {path}")


@dataclass
class ContentPredicate(BasePredicate):
    pattern: str
    regex: bool = False
    case_sensitive: bool = True
    binary_policy: str = "skip"
    _stats: SearchStats | None = field(default=None, init=False, repr=False)
    _warnings: list[str] | None = field(default=None, init=False, repr=False)
    _read_cache: ContentReadCache | None = field(default=None, init=False, repr=False)
    _matches_by_path: dict[Path, list[ContentMatch]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.pattern:
            raise ContentSearchError("content search pattern cannot be empty")
        self._compiled_regex = compile_content_regex(self.pattern, self.case_sensitive) if self.regex else None

    def bind_stats(self, stats: SearchStats, warnings: list[str] | None = None) -> None:
        self._stats = stats
        self._warnings = warnings

    def bind_read_cache(self, cache: ContentReadCache) -> None:
        self._read_cache = cache

    def matches_for(self, path: Path) -> list[ContentMatch]:
        return self._matches_by_path.get(path, [])

    def collect_content_matches(self, entry: FileEntry) -> list[ContentMatch]:
        return self.matches_for(entry.path)

    def clear_entry_caches(self) -> None:
        self._matches_by_path.clear()

    def matches(self, entry: FileEntry) -> bool:
        if not entry.is_file or entry.is_symlink:
            self._matches_by_path[entry.path] = []
            return False
        outcome = find_content_matches(
            entry.path,
            self.pattern,
            regex=self.regex,
            case_sensitive=self.case_sensitive,
            binary_policy=self.binary_policy,
            compiled_regex=self._compiled_regex,
            read_cache=self._read_cache,
        )
        if outcome.binary_skipped:
            _record_binary_skip(entry.path, self._stats, self._warnings)
        if outcome.access_error:
            _record_content_access_error(entry.path, self._stats, self._warnings)
        self._matches_by_path[entry.path] = outcome.matches
        return bool(outcome.matches)


@dataclass
class AndPredicate(BasePredicate):
    predicates: list[Predicate]

    def bind_stats(self, stats: SearchStats, warnings: list[str] | None = None) -> None:
        for predicate in self.predicates:
            predicate.bind_stats(stats, warnings)

    def bind_read_cache(self, cache: ContentReadCache) -> None:
        for predicate in self.predicates:
            predicate.bind_read_cache(cache)

    def matches(self, entry: FileEntry) -> bool:
        return all(predicate.matches(entry) for predicate in self.predicates)

    def collect_content_matches(self, entry: FileEntry) -> list[ContentMatch]:
        groups = [predicate.collect_content_matches(entry) for predicate in self.predicates]
        content_groups = [group for group in groups if group]
        if not content_groups:
            return []
        if len(content_groups) == 1:
            return content_groups[0]
        return _intersect_content_match_lists(content_groups)

    def clear_entry_caches(self) -> None:
        for predicate in self.predicates:
            predicate.clear_entry_caches()


@dataclass
class OrPredicate(BasePredicate):
    predicates: list[Predicate]

    def bind_stats(self, stats: SearchStats, warnings: list[str] | None = None) -> None:
        for predicate in self.predicates:
            predicate.bind_stats(stats, warnings)

    def bind_read_cache(self, cache: ContentReadCache) -> None:
        for predicate in self.predicates:
            predicate.bind_read_cache(cache)

    def matches(self, entry: FileEntry) -> bool:
        matched = False
        for predicate in self.predicates:
            if predicate.matches(entry):
                matched = True
        return matched

    def collect_content_matches(self, entry: FileEntry) -> list[ContentMatch]:
        results: list[ContentMatch] = []
        seen: set[int] = set()
        for predicate in self.predicates:
            for match in predicate.collect_content_matches(entry):
                if match.line_number in seen:
                    continue
                seen.add(match.line_number)
                results.append(match)
        return sorted(results, key=lambda match: match.line_number)

    def clear_entry_caches(self) -> None:
        for predicate in self.predicates:
            predicate.clear_entry_caches()


@dataclass
class NotPredicate(BasePredicate):
    predicate: Predicate

    def bind_stats(self, stats: SearchStats, warnings: list[str] | None = None) -> None:
        self.predicate.bind_stats(stats, warnings)

    def bind_read_cache(self, cache: ContentReadCache) -> None:
        self.predicate.bind_read_cache(cache)

    def matches(self, entry: FileEntry) -> bool:
        return not self.predicate.matches(entry)

    def collect_content_matches(self, entry: FileEntry) -> list[ContentMatch]:
        return []

    def clear_entry_caches(self) -> None:
        self.predicate.clear_entry_caches()


@dataclass
class AlwaysTruePredicate(BasePredicate):
    def matches(self, entry: FileEntry) -> bool:
        return True


def combine_with_and(predicates: list[Predicate]) -> Predicate:
    if not predicates:
        return AlwaysTruePredicate()
    if len(predicates) == 1:
        return predicates[0]
    return AndPredicate(predicates)
