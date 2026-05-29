"""Test the examples queries."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

import pytest

from file_search_tool.dsl import compile_ast, parse_query
from file_search_tool.search import search_with_stats


EXAMPLES_PATH = Path(__file__).resolve().parents[1] / "examples" / "queries.txt"
EXAMPLE_QUERIES = [
    line.strip()
    for line in EXAMPLES_PATH.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.strip().startswith("#")
]


def build_example_tree(root: Path) -> None:
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    old = datetime.now(timezone.utc) - timedelta(days=30)
    recent_ts = recent.timestamp()
    old_ts = old.timestamp()

    app_py = root / "app.py"
    app_py.write_text("TODO\n" + ("x" * 2048), encoding="utf-8")
    os.utime(app_py, (recent_ts, recent_ts))

    readme_md = root / "readme.md"
    readme_md.write_text("", encoding="utf-8")
    os.utime(readme_md, (old_ts, old_ts))

    tests_dir = root / "tests"
    tests_dir.mkdir()
    ignored = tests_dir / "ignored.py"
    ignored.write_text("TODO\n" + ("x" * 2048), encoding="utf-8")
    os.utime(ignored, (recent_ts, recent_ts))


@pytest.mark.parametrize("query", EXAMPLE_QUERIES)
def test_examples_queries_execute_without_error(tmp_path: Path, query: str):
    build_example_tree(tmp_path)
    predicate = compile_ast(parse_query(query))
    list(search_with_stats(tmp_path, predicate).results)
