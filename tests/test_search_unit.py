"""Test the search unit."""

from pathlib import Path

from file_search_tool.filters import AlwaysTruePredicate, ContentPredicate
from file_search_tool.models import SearchOptions, SearchResult, SearchStats
from file_search_tool.search import (
    search,
    search_with_stats,
    sync_stats_for_output,
)


def test_search_wrapper_yields_results(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    results = list(search(tmp_path, AlwaysTruePredicate(), SearchOptions(max_depth=0)))

    assert len(results) == 1
    assert results[0].relative_path.as_posix() == "."


def test_search_with_stats_defer_limit_scans_all_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")

    session = search_with_stats(
        tmp_path,
        AlwaysTruePredicate(),
        SearchOptions(limit=1),
        defer_limit=True,
    )
    results = list(session.results)
    file_results = [result for result in results if result.type == "file"]

    assert len(file_results) == 2
    assert session.stats.stopped_early is False


def test_sync_stats_without_limit_flag(tmp_path: Path):
    stats = SearchStats(stopped_early=False)
    results = [
        SearchResult(Path("a"), Path("a"), "file", 1, 1.0, "path"),
    ]

    sync_stats_for_output(stats, results, limit_applied=False)

    assert stats.files_matched == 1
    assert stats.stopped_early is False


def test_search_emits_directory_path_match(tmp_path: Path):
    (tmp_path / "child").mkdir()

    results = list(
        search_with_stats(
            tmp_path,
            AlwaysTruePredicate(),
            SearchOptions(max_depth=1),
        ).results
    )

    kinds = {result.relative_path.as_posix(): result.type for result in results}
    assert kinds["child"] == "dir"


def test_search_emits_content_line_results(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("alpha\nbravo\n", encoding="utf-8")

    results = list(search_with_stats(tmp_path, ContentPredicate("alpha")).results)

    assert len(results) == 1
    assert results[0].match_kind == "content"
    assert results[0].line_number == 1
