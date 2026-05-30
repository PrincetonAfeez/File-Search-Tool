# File Search Tool

[![Tests](https://github.com/PrincetonAfeez/file-search-tool/actions/workflows/test.yml/badge.svg)](https://github.com/PrincetonAfeez/file-search-tool/actions/workflows/test.yml)

A Python library and CLI that recursively searches files with hand-written
traversal, generators, pathlib, composable predicates, content search, and a
small query DSL.

**Author:** Princeton Afeez · **License:** [MIT](LICENSE) · **Changelog:**
[CHANGELOG.md](CHANGELOG.md)

## Features

- Recursive directory traversal with depth limits, hidden-file filtering,
  exclude globs, and symlink cycle detection
- Composable predicates (`AND` / `OR` / `NOT`) plus a CLI query DSL
- Content search (plain text and regex) with lazy plain output
- Plain, JSON, and grouped tree output formats with optional summary stats
- Zero runtime dependencies — stdlib only (`pathlib`, `argparse`, etc.)
- Library/CLI split: core search code has no CLI imports

## Requirements

- Python **3.11+** (CI also runs on 3.14)

## Install

Library and CLI (editable, recommended for development):

```text
python -m pip install -e ".[dev]"
```

Runtime only (no test tools):

```text
python -m pip install -e .
```

Reproducible development installs (pinned dev dependencies):

```text
python -m pip install -r requirements-dev.lock
python -m pip install -e .
```

Or install loose dev lower bounds from `requirements.txt` when you do not need exact pins:

```text
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Development

Run the full test suite with coverage:

```text
python -m pytest --cov=file_search_tool --cov-report=term-missing
```

Lint and type-check (also run in CI):

```text
ruff check file_search_tool tests
mypy file_search_tool
mypy tests --disable-error-code=no-untyped-def --disable-error-code=no-untyped-call
```

Regenerate the pinned dev lockfile after changing `[project.optional-dependencies].dev`:

```text
pip-compile pyproject.toml --extra dev -o requirements-dev.lock
```

Current quality bar: **99% library coverage** (enforced via `fail_under` in
`pyproject.toml`), strict mypy on `file_search_tool`, and ruff on library +
tests (see the CI badge above for test status).

## Project Layout

```text
file_search_tool/     Core library (traversal, predicates, DSL, formatters)
  cli.py              Command-line entry point (`file-search`)
  search.py           Generator-based search orchestration
  dsl/                Lexer, parser, and AST → predicate compiler
  formatters/         Plain, JSON, and grouped tree output
tests/                Pytest suite (including tests/test_regressions.py)
docs/adr/             Architecture decision records
docs/scope/           Original project scope and planning notes
examples/queries.txt  Sample DSL queries exercised in tests
```

## CLI Examples

```text
file-search . --name "*.py"
file-search . --ext py,md
file-search . --contains TODO
file-search . --contains todo --content-ignore-case
file-search . --size +10MB
file-search . --size -1KB
file-search . --modified-within 7d
file-search . --query "name:*.py AND size:>1KB AND NOT path:*/tests/*"
file-search . --query "(ext:py OR ext:md) AND modified:within:7d"
file-search . --query "contains:TODO" --format json
file-search . --ext py --format tree
file-search . --name "*.py" --query "contains:TODO"
file-search . --contains TODO --binary-error
```

## Query Semantics

- Operator precedence is `NOT > AND > OR`. For example,
  `name:*.py OR name:*.md AND contains:TODO` parses as
  `name:*.py OR (name:*.md AND contains:TODO)`. Use parentheses to override it.
- Boolean operators are case-insensitive: `and`, `or`, and `not` work the same
  as `AND`, `OR`, and `NOT`.
- Content patterns cannot be empty. An empty `--contains` value (or a library
  `ContentPredicate("")`) is rejected with exit code `2`.
- Extension lists cannot be empty. `--ext ,,` and `ext:,,` both fail with exit
  code `2` instead of matching everything or nothing.
- CLI flags and `--query` are combined with implicit **AND** when used together.
- **OR** evaluates every branch so content caches stay consistent; content lines
  from all matching branches are shown.
- **AND** with multiple `contains` filters requires every pattern somewhere in
  the file; only lines that match **all** content filters are emitted. If no
  single line satisfies every pattern, the file is reported as a path match.
- `--limit` applies to matched **files**, not individual content lines. A file
  with many matching lines still counts as one file toward the limit.
- The search root directory is always visited first and appears as `"."` when
  the root is a directory. Use `--type file` or other filters to narrow root
  matches. When the root is a single file, only that file is visited and it
  appears as `"."`.
- DSL queries that fail to parse print `query error:` on stderr and exit with
  code `2`.
- DSL filter values cannot contain spaces because the lexer splits on whitespace.
  Use CLI flags when you need spaces in search text.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | One or more matched files were found |
| 1 | Search completed successfully but found no matches |
| 2 | Invalid CLI, query, or filter input |
| 3 | Expected runtime or search failure (for example missing root, unreadable tree, binary file with `--binary-error`) |

Exit code `0`/`1` are based on matched **files**, not individual content lines.
Both `main()` and `run()` return the same exit codes; `run()` also writes
`query error:` / `error:` messages to stderr before returning `2` or `3`.
Failures that originate inside a `--query` (including invalid `size:` and
`modified:` values) use the `query error:` prefix; CLI-flag validation failures
use `error:` with exit code `2`; traversal and content-search failures during
the scan use `error:` with exit code `3`.

JSON output always prints a valid array. When nothing matches, it prints `[]`
and still returns exit code `1`.

## Output Formats

- **plain** — Streams lazily; best for large trees. With `--binary-error`, plain
  output is buffered so no partial results are printed if a binary file is hit.
- **json** — Collects all matches into a JSON array first.

### JSON result objects

Each element of the JSON array is one `SearchResult` object with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Absolute path to the matched entry |
| `relative_path` | string | Path relative to the search root (`"."` for the root itself) |
| `type` | string | `"file"`, `"dir"`, `"symlink"`, or `"other"` |
| `size` | integer or null | Entry size in bytes when available |
| `mtime` | number or null | Modification time as a Unix timestamp when available |
| `match_kind` | string | `"path"` or `"content"` |
| `line_number` | integer or null | 1-based line number for content matches |
| `line_text` | string or null | Full matched line text for content matches |
| `matched_text` | string or null | Matched substring for content matches |

- **tree** — Groups matches by parent directory (flat grouped view, not a nested tree widget). Content matches render as `name:line: text`.

Sorting (`--sort`) and non-plain formats collect matches before output. When
sorting or using JSON/tree output, the library scans the full tree first and
the CLI applies `--limit` afterward. Summary stats are synchronized with the
limited output in those modes. `--sort size` and `--sort mtime` sort ascending
(smallest or oldest first); entries without a size or mtime (such as directories)
sort **after** files. `--sort name` is case-insensitive.

## Summary Output

`--summary` prints counters to **stderr** after results (so stdout stays pipe-friendly):

| Field | Meaning |
|-------|---------|
| `files` | Regular files scanned during traversal |
| `dirs` | Directories scanned during traversal |
| `matched_files` | Files that satisfied the predicate in the emitted output |
| `content_matches` | Content lines emitted |
| `entries_skipped` | Hidden, excluded, cyclic, or unreadable entries skipped during traversal |
| `permission_errors` | Entries that could not be accessed during traversal or read during content search |
| `binary_skipped` | Binary files skipped during content search |
| `symlink_cycles` | Directory symlink cycles not re-descended when following symlinks |
| `elapsed` | Wall-clock seconds |
| `stopped early` | Present when `--limit` truncated results |

When `--sort`, JSON, or tree output applies a post-scan limit, `files` and
`dirs` still describe the full traversal while `matched_files` and
`content_matches` describe the truncated output.

With **plain** output and `--limit`, traversal stops as soon as the limit is
reached, so `files` and `dirs` reflect only the partial scan. With `--sort`,
JSON, or tree output the full tree is scanned before the limit is applied, so
`files` and `dirs` reflect the whole traversal. Keep this difference in mind
when comparing `--summary` counters across output formats.

## Filters and Matching Rules

- Path/name globs use `fnmatch` rules: `*` does not cross `/`, and `**` is not
  treated as a recursive glob segment.
- `--exclude` patterns follow the same glob rules. With `--ignore-case`, exclude
  patterns are matched case-insensitively. `--exclude` may be repeated; there is
  no positive `--include` filter — narrow matches with `--name`, `--path`, or DSL
  predicates instead.
- Name/path/extension filters support globs. There is no `--regex-path` flag and
  no DSL regex field for paths; use `--regex-name` for regex name matching.
- `--name`/`--path` are matched against every entry, including the search root.
  The root displays as `"."` in output, but name/path filters compare against
  its real basename (e.g. `file-search ./project --name project` matches the
  root directory itself).
- Extension matching uses `Path.suffix`, i.e. only the final extension. A file
  named `archive.tar.gz` matches `--ext gz`, not `--ext tar.gz`.
- `--type` accepts `file`, `dir`, and `symlink`. Special files (FIFOs, sockets,
  block/character devices) are reported with `type: "other"` and cannot be
  selected by `--type`; filter them with name or path patterns instead.
- Content regex is available via `--contains-regex` only; the DSL `contains:`
  field is plain text.
- `--ignore-case` affects path, name, extension, and exclude matching.
  `--content-ignore-case` affects only content search while leaving path/name
  filters case-sensitive. Library callers can also set
  `SearchOptions.content_case_sensitive` directly.
- Content search reads text as UTF-8 and replaces invalid bytes instead of failing.
- `--size` with a bare number means an exact byte match (`1024` matches files of
  exactly 1024 bytes). Prefix forms are comparative: `+10MB` (greater than),
  `-1KB` (less than), `<=1GB`, `>=512B`, or a range like `1KB..5MB`.
- `--modified-before YYYY-MM-DD` is exclusive (`mtime < midnight` on that date).
  `--modified-after YYYY-MM-DD` is inclusive (`mtime >= midnight`). Together
  they partition the timeline without overlap on day boundaries.
- `--modified-within` / `modified:within:` accept durations in hours, days, or
  weeks only: suffix `h`, `d`, or `w` (for example `3h`, `7d`, `2w`). Minutes
  and seconds from the original design spec were intentionally omitted; hours
  are the finest granularity.
- `modified:within` / `--modified-within` uses an exclusive lower bound:
  `mtime > cutoff` (a file exactly on the boundary is excluded).
- With `--follow-symlinks`, directory symlinks may lead outside the given root.
  Cycles are detected and not descended; revisiting a directory via a cycle does
  not emit it twice.
- Regex filters (`--regex-name`, `--contains-regex`) are not sandboxed. This
  tool is intended for trusted local use; malicious patterns can cause slow
  backtracking (ReDoS) on large files.
- Use `--binary-error` to treat binary files as errors during content search
  instead of skipping them silently.

## Known Limitations

- **One match per line:** content search reports the first occurrence on each
  line only (`str.find` / `re.search`, not `findall`). A line containing
  `TODO TODO` emits one content row.
- **Binary probe window:** files are classified as binary when a NUL byte appears
  in the first 4096 bytes. A NUL byte later in a large file is not detected.
- **Case-insensitive regex:** patterns with regex metacharacters use
  `re.IGNORECASE`, which does not cover all Unicode casefold pairs (for example
  `groß` vs `gross`). Literal patterns without metacharacters use Unicode
  casefold matching instead.
- **UTF-8 only:** content is decoded as UTF-8 with replacement; other encodings
  are not auto-detected.

## Design Notes

- The core library does not import CLI or web code.
- Traversal is implemented recursively without `os.walk`.
- Plain output can stream lazily except when `--binary-error` buffers output.
- Hidden files and directories are skipped by default; use `--all` to include
  them.
- OR queries evaluate every branch to keep boolean semantics correct. A
  per-entry `ContentReadCache` ensures each file is still read and decoded only
  once per traversal step, even when several content filters inspect it.
- Content search reads each matched file line-by-line into a cached `list[str]`
  once per traversal step (UTF-8 text mode after a 4096-byte binary probe) so
  multiple predicates can share the same decoded lines without re-reading the
  file. The full line list is still held in memory for the duration of that
  entry's predicate evaluation; very large text files are not processed in
  constant memory.
- Predicate trees and `SearchSession` objects hold per-search caches and stats.
  Build or bind them once per search; they are not thread-safe and should not be
  reused across concurrent or overlapping searches.
- Case-insensitive `--contains` uses `str.casefold()` substring semantics. Some
  Unicode equivalences (e.g. Turkish İ ↔ i) introduce combining marks during
  casefolding and may not match the user's plain pattern. Use `--contains-regex`
  for richer Unicode handling.

## Library Usage

```python
from pathlib import Path

from file_search_tool.filters import NamePredicate
from file_search_tool.models import SearchOptions
from file_search_tool.search import search_with_stats

session = search_with_stats(
    Path("."),
    NamePredicate("*.py"),
    SearchOptions(max_depth=2, limit=10, content_case_sensitive=False),
)

for result in session.results:
    print(result.relative_path)
```

Sorting, formatting, and verbose warning display are CLI concerns. Library
callers receive an iterator of `SearchResult` objects plus `SearchStats` and a
`warnings` list.

Pass `defer_limit=True` to `search_with_stats()` when a caller collects all
matches before applying its own limit (the CLI does this for sorted/JSON/tree
output).
