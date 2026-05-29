"""Plain-text output formatter."""

from __future__ import annotations

from file_search_tool.models import SearchResult, SearchStats


def format_result(result: SearchResult) -> str:
    path = result.relative_path.as_posix()
    if result.match_kind == "content" and result.line_number is not None:
        return f"{path}:{result.line_number}: {result.line_text}"
    return path


def format_summary(stats: SearchStats) -> str:
    suffix = " stopped early" if stats.stopped_early else ""
    return (
        f"summary: files={stats.files_scanned} dirs={stats.dirs_scanned} "
        f"matched_files={stats.files_matched} content_matches={stats.content_matches} "
        f"entries_skipped={stats.entries_skipped} permission_errors={stats.permission_errors} "
        f"binary_skipped={stats.binary_files_skipped} "
        f"symlink_cycles={stats.symlink_cycles_skipped} elapsed={stats.elapsed_seconds:.3f}s{suffix}"
    )
