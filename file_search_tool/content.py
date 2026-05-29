"""Line-by-line content search for file-search-tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from re import Pattern

from file_search_tool.errors import ContentSearchError

_LITERAL_REGEX_METACHAR = re.compile(r"[.^$*+?{}[\]|\\()]")


@dataclass(frozen=True)
class ContentMatch:
    line_number: int
    line_text: str
    matched_text: str


@dataclass(frozen=True)
class ContentSearchOutcome:
    matches: list[ContentMatch]
    binary_skipped: bool = False
    access_error: bool = False


@dataclass(frozen=True)
class PreparedContent:
    """A file's text split into lines, or a reason it could not be read."""

    lines: list[str] | None
    binary_skipped: bool = False
    access_error: bool = False


def compile_content_regex(pattern: str, case_sensitive: bool = True) -> Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ContentSearchError(f"invalid content regex: {pattern}") from exc


def _looks_like_literal_regex(pattern: str) -> bool:
    return _LITERAL_REGEX_METACHAR.search(pattern) is None


def prepare_content(path: Path, binary_policy: str = "skip") -> PreparedContent:
    """Read and decode a file once, returning its lines or why it was skipped."""

    try:
        with path.open("rb") as binary_handle:
            probe = binary_handle.read(4096)
    except OSError:
        return PreparedContent(None, access_error=True)

    if b"\x00" in probe:
        if binary_policy == "error":
            raise ContentSearchError(f"binary file not searchable: {path}")
        return PreparedContent(None, binary_skipped=True)

    lines: list[str] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as text_handle:
            for line in text_handle:
                lines.append(line.rstrip("\n\r"))
    except OSError:
        return PreparedContent(None, access_error=True)

    return PreparedContent(lines)


class ContentReadCache:
    """Memoizes prepared file content so one entry is read once per traversal step.

    The search engine clears this between entries, so it only ever holds the
    content of the entry currently being evaluated by the predicate tree.
    """

    def __init__(self) -> None:
        self._prepared: dict[tuple[Path, str], PreparedContent] = {}

    def prepare(self, path: Path, binary_policy: str) -> PreparedContent:
        key = (path, binary_policy)
        cached = self._prepared.get(key)
        if cached is not None:
            return cached
        prepared = prepare_content(path, binary_policy)
        self._prepared[key] = prepared
        return prepared

    def clear(self) -> None:
        self._prepared.clear()


def _case_insensitive_span(line_text: str, pattern: str) -> tuple[int, int] | None:
    """Return original-string slice bounds for a case-insensitive plain-text match."""

    folded_line = line_text.casefold()
    folded_pattern = pattern.casefold()
    folded_start = folded_line.find(folded_pattern)
    if folded_start < 0:
        return None
    folded_end = folded_start + len(folded_pattern)

    orig_start: int | None = None
    orig_end: int | None = None
    folded_index = 0
    for orig_index, char in enumerate(line_text):
        next_folded = folded_index + len(char.casefold())
        if orig_start is None and folded_index <= folded_start < next_folded:
            orig_start = orig_index
        if orig_end is None and next_folded >= folded_end:
            orig_end = orig_index + 1
        folded_index = next_folded

    if orig_start is None or orig_end is None:
        return None
    return orig_start, orig_end


def _scan_lines(
    lines: list[str],
    pattern: str,
    *,
    regex: bool,
    case_sensitive: bool,
    compiled_regex: Pattern[str] | None,
) -> list[ContentMatch]:
    use_casefold_literal = regex and not case_sensitive and _looks_like_literal_regex(pattern)
    compiled = None if use_casefold_literal else (
        compiled_regex or (compile_content_regex(pattern, case_sensitive) if regex else None)
    )
    matches: list[ContentMatch] = []

    for line_number, line_text in enumerate(lines, start=1):
        if use_casefold_literal:
            span = _case_insensitive_span(line_text, pattern)
            if span is not None:
                start, end = span
                matches.append(ContentMatch(line_number, line_text, line_text[start:end]))
        elif compiled is not None:
            match = compiled.search(line_text)
            if match:
                matches.append(ContentMatch(line_number, line_text, match.group(0)))
        else:
            if case_sensitive:
                index = line_text.find(pattern)
                if index >= 0:
                    matched_text = line_text[index : index + len(pattern)]
                    matches.append(ContentMatch(line_number, line_text, matched_text))
            else:
                span = _case_insensitive_span(line_text, pattern)
                if span is not None:
                    start, end = span
                    matches.append(ContentMatch(line_number, line_text, line_text[start:end]))

    return matches


def find_content_matches(
    path: Path,
    pattern: str,
    *,
    regex: bool = False,
    case_sensitive: bool = True,
    binary_policy: str = "skip",
    compiled_regex: Pattern[str] | None = None,
    read_cache: ContentReadCache | None = None,
) -> ContentSearchOutcome:
    """Return content matches and whether the file was skipped as binary or unreadable."""

    if read_cache is not None:
        prepared = read_cache.prepare(path, binary_policy)
    else:
        prepared = prepare_content(path, binary_policy)

    if prepared.access_error:
        return ContentSearchOutcome([], access_error=True)
    if prepared.binary_skipped or prepared.lines is None:
        return ContentSearchOutcome([], binary_skipped=prepared.binary_skipped)

    matches = _scan_lines(
        prepared.lines,
        pattern,
        regex=regex,
        case_sensitive=case_sensitive,
        compiled_regex=compiled_regex,
    )
    return ContentSearchOutcome(matches)
