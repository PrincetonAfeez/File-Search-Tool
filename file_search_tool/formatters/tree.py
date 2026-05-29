"""Simple tree-style output formatter."""

from __future__ import annotations

from collections import defaultdict

from file_search_tool.models import SearchResult


def format_results(results: list[SearchResult]) -> str:
    grouped: dict[str, list[SearchResult]] = defaultdict(list)
    for result in results:
        parent = result.relative_path.parent.as_posix()
        if parent == ".":
            parent = ""
        grouped[parent].append(result)

    lines: list[str] = []
    for directory in sorted(grouped):
        if directory:
            lines.append(f"{directory}/")
        for result in sorted(grouped[directory], key=lambda item: item.relative_path.name.casefold()):
            prefix = "  " if directory else ""
            if result.match_kind == "content" and result.line_number is not None:
                lines.append(f"{prefix}{result.relative_path.name}:{result.line_number}: {result.line_text}")
            else:
                lines.append(f"{prefix}{result.relative_path.name}")
    return "\n".join(lines)

