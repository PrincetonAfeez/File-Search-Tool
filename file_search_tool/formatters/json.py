"""JSON output formatter."""

from __future__ import annotations

from dataclasses import asdict
import json as std_json

from file_search_tool.models import SearchResult


def _result_to_dict(result: SearchResult) -> dict[str, object]:
    data = asdict(result)
    data["path"] = str(result.path)
    data["relative_path"] = result.relative_path.as_posix()
    return data


def format_results(results: list[SearchResult]) -> str:
    return std_json.dumps([_result_to_dict(result) for result in results], indent=2)

