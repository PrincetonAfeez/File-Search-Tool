"""Dataclasses used by the file search engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class FileEntry:
    """One filesystem item discovered during traversal."""

    path: Path
    root: Path
    relative_path: Path
    is_file: bool
    is_dir: bool
    is_symlink: bool
    size: int | None
    mtime: float | None
    depth: int


@dataclass(frozen=True)
class SearchResult:
    """One search result, either a path match or a content-line match."""

    path: Path
    relative_path: Path
    type: str
    size: int | None
    mtime: float | None
    match_kind: str
    line_number: int | None = None
    line_text: str | None = None
    matched_text: str | None = None


@dataclass
class SearchOptions:
    """Options controlling traversal and filtering for the library search engine."""

    include_hidden: bool = False
    follow_symlinks: bool = False
    max_depth: int | None = None
    exclude_patterns: list[str] = field(default_factory=list)
    case_sensitive: bool = True
    content_case_sensitive: bool | None = None
    limit: int | None = None
    binary_policy: str = "skip"


@dataclass
class CliDisplayOptions:
    """CLI-only options for formatting, sorting, and diagnostics."""

    sort_by: str | None = None
    output_format: str = "plain"
    show_summary: bool = False
    verbose: bool = False


@dataclass
class SearchStats:
    """Counters describing what happened during a search."""

    files_scanned: int = 0
    dirs_scanned: int = 0
    files_matched: int = 0
    content_matches: int = 0
    entries_skipped: int = 0
    permission_errors: int = 0
    binary_files_skipped: int = 0
    symlink_cycles_skipped: int = 0
    elapsed_seconds: float = 0.0
    stopped_early: bool = False
    _binary_paths_counted: set[Path] = field(default_factory=set, repr=False, compare=False)

    def record_binary_skip(self, path: Path) -> bool:
        """Count a binary skip once per path. Returns True if newly counted."""

        if path in self._binary_paths_counted:
            return False
        self._binary_paths_counted.add(path)
        self.binary_files_skipped += 1
        return True


@dataclass
class SearchSession:
    """A search result iterator plus mutable stats and warnings."""

    results: Iterator[SearchResult]
    stats: SearchStats
    warnings: list[str] = field(default_factory=list)
