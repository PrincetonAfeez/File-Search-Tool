"""Test the formatters."""

from pathlib import Path

from file_search_tool.formatters import json as json_formatter
from file_search_tool.formatters import plain, tree
from file_search_tool.models import SearchResult, SearchStats


def result(path: Path, root: Path, *, line_number=None):
    return SearchResult(
        path=path,
        relative_path=path.relative_to(root),
        type="file",
        size=1,
        mtime=1.0,
        match_kind="content" if line_number else "path",
        line_number=line_number,
        line_text="TODO" if line_number else None,
        matched_text="TODO" if line_number else None,
    )


def test_plain_formats_path_result(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")

    assert plain.format_result(result(path, tmp_path)) == "app.py"


def test_plain_formats_content_result(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")

    assert plain.format_result(result(path, tmp_path, line_number=2)) == "app.py:2: TODO"


def test_json_formatter_outputs_array(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")

    assert '"relative_path": "app.py"' in json_formatter.format_results([result(path, tmp_path)])


def test_tree_formatter_groups_by_directory(tmp_path: Path):
    (tmp_path / "src").mkdir()
    path = tmp_path / "src" / "app.py"
    path.write_text("", encoding="utf-8")

    output = tree.format_results([result(path, tmp_path)])

    assert "src/" in output
    assert "  app.py" in output


def test_tree_formatter_renders_root_level_files(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("", encoding="utf-8")

    output = tree.format_results([result(path, tmp_path)])

    assert output == "app.py"


def test_summary_mentions_early_stop():
    stats = SearchStats(stopped_early=True)

    assert "stopped early" in plain.format_summary(stats)


def test_summary_includes_symlink_cycles():
    stats = SearchStats(symlink_cycles_skipped=2)

    assert "symlink_cycles=2" in plain.format_summary(stats)

