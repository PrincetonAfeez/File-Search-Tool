"""Small shared helpers."""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path


def relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def normalize_relative_path(path: Path) -> str:
    text = path.as_posix()
    return "." if text == "" else text


def is_hidden_relative(relative_path: Path) -> bool:
    return any(part.startswith(".") for part in relative_path.parts if part not in ("", "."))


def matches_any_pattern(
    name: str,
    relative_path: Path,
    patterns: list[str],
    *,
    case_sensitive: bool = True,
) -> bool:
    normalized = normalize_relative_path(relative_path)
    if case_sensitive:
        return any(fnmatchcase(name, pattern) or fnmatchcase(normalized, pattern) for pattern in patterns)
    folded_name = name.casefold()
    folded_path = normalized.casefold()
    return any(
        fnmatchcase(folded_name, pattern.casefold()) or fnmatchcase(folded_path, pattern.casefold())
        for pattern in patterns
    )


def entry_type(is_file: bool, is_dir: bool, is_symlink: bool) -> str:
    if is_symlink:
        return "symlink"
    if is_dir:
        return "dir"
    if is_file:
        return "file"
    return "other"


def sort_key_text(value: str, case_sensitive: bool) -> str:
    return value if case_sensitive else value.casefold()


def split_csv_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]
