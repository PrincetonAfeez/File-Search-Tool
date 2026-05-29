"""Search engine connecting traversal, predicates, and results."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time
from typing import Iterator

from file_search_tool.content import ContentMatch, ContentReadCache
from file_search_tool.filters import AlwaysTruePredicate, Predicate
from file_search_tool.models import FileEntry, SearchOptions, SearchResult, SearchSession, SearchStats
from file_search_tool.traversal import walk
from file_search_tool.utils import entry_type


def _path_result(entry: FileEntry) -> SearchResult:
    return SearchResult(
        path=entry.path,
        relative_path=entry.relative_path,
        type=entry_type(entry.is_file, entry.is_dir, entry.is_symlink),
        size=entry.size,
        mtime=entry.mtime,
        match_kind="path",
    )


def _content_result(entry: FileEntry, match: ContentMatch) -> SearchResult:
    return SearchResult(
        path=entry.path,
        relative_path=entry.relative_path,
        type=entry_type(entry.is_file, entry.is_dir, entry.is_symlink),
        size=entry.size,
        mtime=entry.mtime,
        match_kind="content",
        line_number=match.line_number,
        line_text=match.line_text,
        matched_text=match.matched_text,
    )


def count_unique_matched_files(results: list[SearchResult]) -> int:
    return len({result.relative_path.as_posix() for result in results})


def sync_stats_for_output(stats: SearchStats, results: list[SearchResult], *, limit_applied: bool) -> None:
    """Align summary counters with post-processed CLI output."""

    stats.files_matched = count_unique_matched_files(results)
    stats.content_matches = sum(1 for result in results if result.match_kind == "content")
    if limit_applied:
        stats.stopped_early = True


def search(
    root: Path,
    predicate: Predicate | None = None,
    options: SearchOptions | None = None,
) -> Iterator[SearchResult]:
    return search_with_stats(root, predicate, options).results


def search_with_stats(
    root: Path,
    predicate: Predicate | None = None,
    options: SearchOptions | None = None,
    *,
    defer_limit: bool = False,
) -> SearchSession:
    options = options or SearchOptions()
    if defer_limit:
        options = replace(options, limit=None)
    predicate = predicate or AlwaysTruePredicate()
    stats = SearchStats()
    warnings: list[str] = []
    read_cache = ContentReadCache()
    predicate.bind_stats(stats, warnings)
    predicate.bind_read_cache(read_cache)

    def generate() -> Iterator[SearchResult]:
        start = time.perf_counter()
        try:
            for entry in walk(Path(root), options, stats, warnings):
                read_cache.clear()
                predicate.clear_entry_caches()
                if not predicate.matches(entry):
                    continue

                content_matches = predicate.collect_content_matches(entry)
                if content_matches:
                    results = [_content_result(entry, match) for match in content_matches]
                else:
                    results = [_path_result(entry)]

                stats.files_matched += 1
                for result in results:
                    if result.match_kind == "content":
                        stats.content_matches += 1
                    yield result

                if options.limit is not None and stats.files_matched >= options.limit:
                    stats.stopped_early = True
                    return
        finally:
            read_cache.clear()
            predicate.clear_entry_caches()
            stats.elapsed_seconds = time.perf_counter() - start

    return SearchSession(generate(), stats, warnings)
