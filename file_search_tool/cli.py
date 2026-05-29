"""Command-line interface for file-search-tool."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
import math
from pathlib import Path
import sys
from typing import TextIO

from file_search_tool.errors import FileSearchError, QuerySyntaxError
from file_search_tool.formatters import json as json_formatter
from file_search_tool.formatters import plain as plain_formatter
from file_search_tool.formatters import tree as tree_formatter
from file_search_tool.models import CliDisplayOptions, SearchOptions, SearchResult
from file_search_tool.options import options_from_namespace, predicate_from_namespace
from file_search_tool.search import count_unique_matched_files, search_with_stats, sync_stats_for_output
from file_search_tool.utils import sort_key_text


def _package_version() -> str:
    try:
        return version("file-search-tool")
    except PackageNotFoundError:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="file-search", description="Search files recursively with pathlib.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    parser.add_argument("root", help="Root file or directory to search.")

    parser.add_argument("--name", help="Glob pattern matched against file or directory names.")
    parser.add_argument("--regex-name", help="Regex matched against file or directory names.")
    parser.add_argument("--path", dest="path_pattern", help="Glob pattern matched against normalized relative paths.")
    parser.add_argument("--ext", help="Comma-separated extensions such as py,md,txt.")
    parser.add_argument("--type", dest="entry_type", choices=["file", "dir", "symlink"], help="Entry type to match.")
    parser.add_argument("--size", help="Size expression: +10MB (greater), -1KB (less), <=1GB, 1KB..5MB, or 1024 (exact bytes).")
    parser.add_argument("--modified-before", help="Match entries modified before YYYY-MM-DD.")
    parser.add_argument("--modified-after", help="Match entries modified at or after YYYY-MM-DD.")
    parser.add_argument("--modified-within", help="Match entries modified within a duration: 3h, 7d, or 2w.")
    parser.add_argument("--contains", help="Plain text to search for inside files.")
    parser.add_argument("--contains-regex", help="Regex to search for inside files.")
    parser.add_argument("--query", help="DSL query, for example: name:*.py AND contains:TODO.")

    parser.add_argument("--depth", type=int, help="Maximum traversal depth; root is depth 0.")
    parser.add_argument("--exclude", action="append", help="Exclude glob pattern. May be repeated.")
    parser.add_argument("--all", dest="include_hidden", action="store_true", help="Include hidden files and directories.")
    parser.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories and avoid cycles.")
    parser.add_argument("--ignore-case", action="store_true", help="Use case-insensitive matching for filters and excludes.")
    parser.add_argument("--case-sensitive", action="store_true", help="Use case-sensitive matching explicitly.")
    parser.add_argument(
        "--content-ignore-case",
        action="store_true",
        help="Use case-insensitive content matching while keeping path/name filters case-sensitive.",
    )
    parser.add_argument("--binary-error", action="store_true", help="Treat binary files as errors during content search.")
    parser.add_argument("--limit", type=int, help="Maximum number of matched files to return.")
    parser.add_argument("--sort", choices=["name", "size", "mtime"], help="Sort results; requires collecting matches first.")
    parser.add_argument("--format", dest="output_format", choices=["plain", "tree", "json"], default="plain")
    parser.add_argument("--summary", action="store_true", help="Print summary stats after results.")
    parser.add_argument("--verbose", action="store_true", help="Print traversal and content warnings.")
    return parser


def _sort_results(results: list[SearchResult], sort_by: str | None) -> list[SearchResult]:
    if sort_by == "name":
        return sorted(
            results,
            key=lambda result: sort_key_text(result.relative_path.as_posix(), case_sensitive=False),
        )
    if sort_by == "size":
        return sorted(
            results,
            key=lambda result: (math.inf if result.size is None else result.size, result.relative_path.as_posix()),
        )
    if sort_by == "mtime":
        return sorted(
            results,
            key=lambda result: (math.inf if result.mtime is None else result.mtime, result.relative_path.as_posix()),
        )
    return results


def _apply_file_limit(results: list[SearchResult], limit: int | None) -> list[SearchResult]:
    if limit is None:
        return results
    allowed_paths: set[str] = set()
    limited: list[SearchResult] = []
    for result in results:
        path_key = result.relative_path.as_posix()
        if path_key not in allowed_paths:
            if len(allowed_paths) >= limit:
                continue
            allowed_paths.add(path_key)
        limited.append(result)
    return limited


def _print_warnings(warnings: list[str], stderr: TextIO) -> None:
    for warning in warnings:
        print(f"warning: {warning}", file=stderr)


def _needs_deferred_limit(display: CliDisplayOptions, search_limit: int | None) -> bool:
    if search_limit is None:
        return False
    return display.sort_by is not None or display.output_format in {"json", "tree"}


def _should_buffer_plain_output(search_options: SearchOptions) -> bool:
    return search_options.binary_policy == "error"


def run(args: argparse.Namespace, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        search_options, display_options = options_from_namespace(args)
        predicate = predicate_from_namespace(args, search_options)
        defer_limit = _needs_deferred_limit(display_options, search_options.limit)
        session = search_with_stats(Path(args.root), predicate, search_options, defer_limit=defer_limit)

        matched_files = 0
        if display_options.output_format in {"json", "tree"} or display_options.sort_by is not None:
            results = list(session.results)
            results = _sort_results(results, display_options.sort_by)
            pre_limit_files = count_unique_matched_files(results)
            results = _apply_file_limit(results, search_options.limit)
            if search_options.limit is not None:
                sync_stats_for_output(
                    session.stats,
                    results,
                    limit_applied=pre_limit_files > search_options.limit,
                )
            matched_files = count_unique_matched_files(results)

            if display_options.output_format == "json":
                print(json_formatter.format_results(results), file=stdout)
            elif display_options.output_format == "tree":
                output = tree_formatter.format_results(results)
                if output:
                    print(output, file=stdout)
            else:
                for result in results:
                    print(plain_formatter.format_result(result), file=stdout)
        else:
            seen_paths: set[str] = set()
            buffered_lines: list[str] = []
            buffer_plain = _should_buffer_plain_output(search_options)
            for result in session.results:
                seen_paths.add(result.relative_path.as_posix())
                line = plain_formatter.format_result(result)
                if buffer_plain:
                    buffered_lines.append(line)
                else:
                    print(line, file=stdout)
            if buffer_plain:
                for line in buffered_lines:
                    print(line, file=stdout)
            matched_files = len(seen_paths)

        if display_options.verbose:
            _print_warnings(session.warnings, stderr)
        if display_options.show_summary:
            print(plain_formatter.format_summary(session.stats), file=stderr)

        return 0 if matched_files > 0 else 1
    except QuerySyntaxError as exc:
        print(f"query error: {exc}", file=stderr)
        return 2
    except FileSearchError as exc:
        print(f"error: {exc}", file=stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
