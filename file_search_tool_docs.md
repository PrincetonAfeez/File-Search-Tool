# Architecture Decision Record
## App — File Search Tool
**Filesystem Utilities Group | Document 1 of 5**
**Status: Accepted**

---

## Context

The Filesystem Utilities group requires a Python library and command-line tool for recursively searching files and directories. The tool must support path-based filters, content search, query composition, output formats, summary statistics, and predictable shell exit codes while remaining small enough to understand as an academic systems project.

The repository is intentionally a library plus CLI, not a web application. The core search package has no CLI imports, no database, no daemon, and no external runtime dependencies. The implementation uses `pathlib`, recursive traversal, generators, dataclasses, composable predicates, and a small query DSL.

The central design decision is to keep traversal, predicate evaluation, content scanning, formatting, and CLI parsing as separate layers. The library exposes `search()` and `search_with_stats()`, while the CLI builds `SearchOptions`, compiles flags and DSL queries into predicates, chooses output behavior, and maps expected failures to exit codes.

---

## Decisions

### Decision 1 — Build a standard-library-only runtime

**Chosen:** Use only the Python standard library at runtime.

**Rejected:** Rich CLI frameworks, external glob/path libraries, ripgrep-style engines, or database-backed indexing.

**Reason:** The learning goal is to demonstrate filesystem traversal, generators, predicate composition, parsing, and CLI discipline directly. Zero runtime dependencies make the tool portable and make the source of behavior visible.

---

### Decision 2 — Library/CLI split

**Chosen:** Keep `file_search_tool.search`, traversal, filters, DSL, and formatters independent from the CLI entry point.

**Rejected:** Implementing all behavior inside `cli.py`.

**Reason:** Library callers should be able to search from Python without shell parsing, stdout, stderr, or process exit codes. The CLI should translate user input into library options, not own the search algorithm.

---

### Decision 3 — Recursive traversal by hand

**Chosen:** Implement recursive traversal in `traversal.py` without relying on `os.walk`.

**Rejected:** Delegating traversal completely to `os.walk`.

**Reason:** Hand-written traversal makes hidden filtering, exclude patterns, depth limits, permission handling, symlink-cycle detection, root handling, and stats updates explicit and testable.

---

### Decision 4 — Yield `FileEntry` objects before applying predicates

**Chosen:** Traversal produces `FileEntry` dataclasses containing path, root, relative path, type booleans, size, mtime, and depth.

**Rejected:** Having traversal return raw `Path` objects only.

**Reason:** Predicates need consistent metadata. A typed entry object avoids repeated `stat()` logic across filters and makes test fixtures easier to reason about.

---

### Decision 5 — Predicate protocol and composable filters

**Chosen:** Define a predicate protocol with `matches()`, `bind_stats()`, `bind_read_cache()`, `collect_content_matches()`, and `clear_entry_caches()`.

**Rejected:** A single monolithic if/else filter function.

**Reason:** Name, path, extension, type, size, modified-time, content, AND, OR, NOT, and always-true behavior can all share one interface. This makes CLI flags and DSL expressions compile into the same predicate tree.

---

### Decision 6 — Small DSL instead of full query language

**Chosen:** Implement a small query DSL with fields, `AND`, `OR`, `NOT`, and parentheses.

**Rejected:** SQL-like syntax, regex path syntax, quoting, phrase parsing, or a full grammar package.

**Reason:** The DSL gives users useful composition without requiring a third-party parser. The recursive-descent parser is small, visible, and testable. The known trade-off is that DSL values cannot contain spaces.

---

### Decision 7 — CLI flags and DSL queries combine with implicit AND

**Chosen:** If a user provides both flags and `--query`, all predicates are combined with AND.

**Rejected:** Letting `--query` override flags or requiring the user to express everything in one place.

**Reason:** This makes the CLI predictable: every supplied constraint narrows the result set. It also allows simple flags to be mixed with advanced query expressions.

---

### Decision 8 — Content search is line-oriented

**Chosen:** Content search reads UTF-8 text with replacement, scans line-by-line, and reports the first match per line.

**Rejected:** Binary grep, encoding detection, all matches per line, or constant-memory multi-predicate content scanning.

**Reason:** Line-oriented search is useful and simple. Reporting one match per line keeps output concise. UTF-8 replacement avoids decode crashes while still staying text-focused.

---

### Decision 9 — Per-entry content cache

**Chosen:** `ContentReadCache` memoizes prepared content for the current traversal entry and is cleared between entries.

**Rejected:** Reading a file once for each content predicate, or caching all file content globally.

**Reason:** AND/OR predicate trees may contain multiple content checks. Per-entry caching prevents repeated file reads while keeping memory bounded to one entry at a time.

---

### Decision 10 — OR evaluates every branch

**Chosen:** OR predicates evaluate every branch instead of short-circuiting.

**Rejected:** Short-circuit OR.

**Reason:** Content result collection needs all matching content branches so output lines remain complete and consistent. The per-entry read cache controls the cost of evaluating multiple content branches.

---

### Decision 11 — Hidden files skipped by default

**Chosen:** Skip hidden files/directories by default and include them with `--all`.

**Rejected:** Include hidden files by default.

**Reason:** This mirrors common CLI expectations for search tools and avoids noisy `.git`, virtualenv, and cache directories unless the user opts in.

---

### Decision 12 — Symlink following is opt-in with cycle detection

**Chosen:** Do not follow symlinked directories unless `--follow-symlinks` is set. When following, track directory identity to avoid cycles.

**Rejected:** Always following symlinks or never supporting symlink traversal.

**Reason:** Symlinks are useful but dangerous for recursive traversal. Opt-in following with cycle detection gives power users control without surprising default behavior.

---

### Decision 13 — Plain output streams; JSON/tree/sort collect

**Chosen:** Plain output streams lazily by default. JSON, tree, and sorted output collect results before formatting.

**Rejected:** Collect all results for every format.

**Reason:** Plain output should work well for large trees and pipelines. JSON/tree/sort require whole-result knowledge, so they intentionally trade memory for structured output.

---

### Decision 14 — Exit code reflects matched files

**Chosen:** Exit code `0` means one or more matched files, `1` means successful search with no matched files, and `2` means expected error.

**Rejected:** Returning `0` for every successful search regardless of matches.

**Reason:** Shell users need to branch on whether anything matched. The rule is based on unique matched files, not content-line count.

---

## Consequences

**Positive:**
- Runtime install has zero dependencies.
- Library API is reusable independently of CLI.
- Traversal behavior is explicit and testable.
- Predicate trees support both flags and DSL expressions.
- Content matching can share decoded lines across predicate branches.
- Plain output can stream lazily.
- JSON/tree/sort behavior is deliberate and documented.
- Stats and warnings make operational behavior visible.
- CI checks multiple Python versions with tests, ruff, and mypy.

**Negative / Trade-offs:**
- No persistent index; every search walks the filesystem.
- DSL values cannot contain spaces.
- Content search is UTF-8 with replacement only.
- Regex patterns are not sandboxed.
- Binary detection only scans the first 4096 bytes for NUL.
- One content match is emitted per line.
- Very large text files are loaded into a list of lines per entry while predicates evaluate.
- JSON/tree/sort collect matches before output.

---

## Alternatives Not Explored

- Persistent SQLite or inverted index.
- Watchman-style background indexer.
- Parallel traversal.
- ripgrep-compatible regex engine.
- Quoted/escaped DSL strings.
- Recursive `**` glob semantics.
- Full nested tree widget output.
- Binary content search.
- Encoding autodetection.

---

*Constitution reference: Article 1 (Python fundamentals and architecture), Article 3.3 (scope discipline), Article 4 (quality proportional to scope), Article 6 (behavior verification), and Article 7 (progressive complexity).*

---


# Technical Design Document
## App — File Search Tool
**Filesystem Utilities Group | Document 2 of 5**

---

## Overview

File Search Tool is a Python 3.11+ filesystem search library and CLI. It recursively traverses a root file or directory, applies composable predicates, optionally searches file content, and emits path/content results in plain, JSON, or grouped tree format.

**Package:** `file_search_tool`  
**Console script:** `file-search`  
**Runtime dependencies:** none  
**Dev dependencies:** pytest, pytest-cov, ruff, mypy  
**Primary public API:** `search()` and `search_with_stats()`  
**Primary CLI entry:** `file_search_tool.cli:main`

---

## Data Flow

### CLI search flow

```text
file-search <root> [filters] [display options]
  │
  ▼
argparse namespace
  │
  ├── options_from_namespace()
  │     ├── SearchOptions
  │     └── CliDisplayOptions
  │
  ├── predicate_from_namespace()
  │     ├── flag predicates
  │     ├── optional DSL predicate
  │     └── combine_with_and()
  │
  ▼
search_with_stats(root, predicate, options, defer_limit=...)
  │
  ▼
SearchSession(results iterator, stats, warnings)
  │
  ├── plain streaming path
  └── collect path for json/tree/sort
  │
  ▼
formatter
  │
  ├── stdout results
  ├── stderr warnings when --verbose
  └── stderr summary when --summary
```

---

### Library search flow

```text
search_with_stats()
  │
  ├── build SearchStats
  ├── build warnings list
  ├── build ContentReadCache
  ├── bind stats/cache to predicate tree
  │
  ▼
generator
  │
  ├── walk(root, options, stats, warnings)
  ├── clear per-entry content cache
  ├── predicate.matches(entry)
  ├── predicate.collect_content_matches(entry)
  ├── emit content SearchResult(s) or path SearchResult
  └── stop early when streaming limit reached
```

---

### Traversal flow

```text
walk(root, options)
  │
  ├── expanduser + validate root exists
  ├── resolve root
  ├── recurse(path, depth)
  │     ├── compute relative path
  │     ├── skip hidden unless --all
  │     ├── skip exclude patterns
  │     ├── stat/lstat entry
  │     ├── detect symlink cycle when following
  │     ├── update file/dir stats
  │     ├── yield FileEntry
  │     └── sorted children recursion
  └── record warnings and skipped counters on access errors
```

---

### DSL flow

```text
query string
  │
  ▼
lex()
  │
  ▼
Parser.parse()
  ├── OR level
  ├── AND level
  ├── NOT level
  └── primary/filter level
  │
  ▼
AST nodes
  │
  ▼
compile_ast()
  │
  └── Predicate tree
```

---

## Module-Level Structure

```text
file_search_tool/
  __init__.py
  cli.py
  content.py
  dateparse.py
  errors.py
  filters.py
  matcher.py
  models.py
  options.py
  search.py
  sizeparse.py
  traversal.py
  utils.py
  dsl/
    __init__.py
    ast.py
    lexer.py
    parser.py
    predicates.py
    tokens.py
  formatters/
    __init__.py
    plain.py
    json.py
    tree.py

tests/
  test_*.py
  test_regressions.py

docs/
  adr/
  scope/

examples/
  queries.txt

pyproject.toml
requirements.txt
README.md
CHANGELOG.md
.github/workflows/test.yml
```

---

## Module Dependency Graph

```text
cli.py
  ├── argparse / sys
  ├── options.options_from_namespace
  ├── options.predicate_from_namespace
  ├── search.search_with_stats
  ├── search.sync_stats_for_output
  ├── formatters.plain/json/tree
  └── errors.FileSearchError / QuerySyntaxError

options.py
  ├── dateparse
  ├── dsl.parse_query / compile_ast
  ├── filters
  ├── sizeparse
  └── models.SearchOptions / CliDisplayOptions

search.py
  ├── content.ContentReadCache
  ├── filters.Predicate
  ├── traversal.walk
  ├── models
  └── utils.entry_type

traversal.py
  ├── pathlib.Path
  ├── stat
  ├── models.FileEntry / SearchOptions / SearchStats
  └── utils hidden/exclude/relative helpers

filters.py
  ├── content.find_content_matches
  ├── dateparse.ModifiedTimeFilter
  ├── sizeparse.SizeFilter
  ├── matcher glob/regex helpers
  └── models.FileEntry / SearchStats

dsl.parser
  ├── dsl.lexer
  ├── dsl.ast
  └── errors.QuerySyntaxError

dsl.predicates
  ├── dsl.ast
  ├── filters predicate classes
  ├── sizeparse
  └── dateparse

formatters
  └── models.SearchResult / SearchStats
```

---

## Core Data Structures

### `FileEntry`

Represents one filesystem item discovered during traversal.

Fields:
- `path`
- `root`
- `relative_path`
- `is_file`
- `is_dir`
- `is_symlink`
- `size`
- `mtime`
- `depth`

---

### `SearchResult`

Represents either a path match or a content-line match.

Fields:
- `path`
- `relative_path`
- `type`
- `size`
- `mtime`
- `match_kind`
- `line_number`
- `line_text`
- `matched_text`

`match_kind` is:
- `path`
- `content`

---

### `SearchOptions`

Library search behavior:

```python
SearchOptions(
    include_hidden=False,
    follow_symlinks=False,
    max_depth=None,
    exclude_patterns=[],
    case_sensitive=True,
    content_case_sensitive=None,
    limit=None,
    binary_policy="skip",
)
```

---

### `CliDisplayOptions`

CLI-only output behavior:

```python
CliDisplayOptions(
    sort_by=None,
    output_format="plain",
    show_summary=False,
    verbose=False,
)
```

---

### `SearchStats`

Counters:
- files scanned
- directories scanned
- matched files
- content matches
- entries skipped
- permission errors
- binary files skipped
- symlink cycles skipped
- elapsed seconds
- stopped early flag

`record_binary_skip()` deduplicates binary skip counting per path.

---

### `SearchSession`

A container for:
- result iterator
- mutable stats
- warnings list

---

### `ContentMatch`

Represents one content match:
- line number
- full line text
- matched text

---

### `PreparedContent`

Represents decoded file content or skip/error state:
- `lines`
- `binary_skipped`
- `access_error`

---

### `SizeFilter`

Represents parsed size expression:
- exact
- greater than
- greater than or equal
- less than
- less than or equal
- range

---

### `ModifiedTimeFilter`

Represents parsed modified-time expression:
- before
- after
- within

---

## Function and Class Reference

### `search(root, predicate=None, options=None)`

Convenience API. Returns only an iterator of `SearchResult`.

---

### `search_with_stats(root, predicate=None, options=None, defer_limit=False)`

Main library API. Returns `SearchSession`.

Responsibilities:
- create stats and warnings
- bind predicate state
- create per-entry content cache
- invoke traversal
- emit path/content search results
- update stats
- enforce streaming limit unless deferred

---

### `walk(root, options, stats=None, warnings=None)`

Recursive filesystem traversal generator.

Responsibilities:
- root validation
- hidden file filtering
- exclude pattern filtering
- file/dir/symlink metadata
- max-depth handling
- optional symlink following
- symlink cycle detection
- sorted child traversal
- stats and warning updates

---

### `ContentPredicate`

Searches file contents.

Behavior:
- skips non-files and symlinks
- prepares file content through `find_content_matches()`
- records binary skips and access errors
- stores matches by path for later result emission

---

### `AndPredicate`

All child predicates must match. If multiple content predicates produce line matches, the emitted content lines are the intersection of matching line numbers.

---

### `OrPredicate`

Evaluates every child predicate and returns true when any child matches. Content lines are unioned by line number.

---

### `NotPredicate`

Negates its child predicate. Does not emit content matches.

---

### `parse_query(query)`

Lexes and parses the DSL into AST nodes.

Precedence:
```text
NOT > AND > OR
```

Supports:
- parentheses
- `field:value` filters
- case-insensitive boolean operators

---

### `compile_ast(node, case_sensitive=True, content_case_sensitive=None, binary_policy="skip")`

Converts DSL AST nodes into predicate objects.

Supported fields:
- `name`
- `path`
- `ext`
- `type`
- `size`
- `modified`
- `contains`

---

### `prepare_content(path, binary_policy="skip")`

Reads file content for content search.

Behavior:
- reads first 4096 bytes as binary probe
- treats NUL byte as binary
- binary policy `skip` returns a skip outcome
- binary policy `error` raises `ContentSearchError`
- text is opened as UTF-8 with replacement
- line endings are stripped

---

### `find_content_matches(...)`

Returns `ContentSearchOutcome` containing line matches plus binary/access state.

Supports:
- literal search
- regex search
- case-sensitive or case-insensitive search
- compiled regex reuse
- per-entry read cache

---

### `parse_size_expression(text)`

Accepts:
- exact bytes or units: `1024`, `1KB`
- greater: `+10MB`, `>10MB`
- greater/equal: `>=512B`
- less: `-1KB`, `<1KB`
- less/equal: `<=1GB`
- range: `1KB..5MB`

Units:
- B
- KB
- MB
- GB
- TB

---

### `parse_modified_expression(text)`

Accepts:
- `before:YYYY-MM-DD`
- `after:YYYY-MM-DD`
- `within:7d`

Durations support:
- hours (`h`)
- days (`d`)
- weeks (`w`)

---

### `options_from_namespace(args)`

Builds `SearchOptions` and `CliDisplayOptions` from parsed CLI arguments.

Validates:
- `--ignore-case` and `--case-sensitive` conflict
- depth must be >= 0
- limit must be > 0
- exclude patterns cannot be empty

---

### `predicate_from_namespace(args, options)`

Builds a predicate tree from CLI flags and optional DSL query. All predicates are combined with AND.

---

### Formatters

#### Plain

Path match:
```text
relative/path.txt
```

Content match:
```text
relative/path.txt:12: matched line text
```

Summary:
```text
summary: files=... dirs=... matched_files=... content_matches=... elapsed=...s
```

#### JSON

Returns an indented JSON array of result objects.

#### Tree

Groups matches by parent directory in a flat tree-style view.

---

## Error Handling Strategy

All expected errors inherit from `FileSearchError`.

Important error classes:
- `TraversalError`
- `QuerySyntaxError`
- `InvalidSizeExpression`
- `InvalidDateExpression`
- `InvalidFilterError`
- `ContentSearchError`
- `CLIError`

CLI behavior:
- DSL failures print `query error: ...`
- other expected failures print `error: ...`
- expected failures return exit code `2`

---

## External Dependencies

### Runtime

None.

### Development

- pytest
- pytest-cov
- ruff
- mypy

---

## Concurrency Model

The app is synchronous and single-process.

Important state rule:
- `SearchSession`, predicate trees, content caches, stats, and warnings are per-search objects.
- They are not thread-safe and should not be reused across concurrent searches.

---

## Performance Characteristics

- Plain output streams lazily unless `--binary-error` requires buffering.
- JSON/tree/sorted output collect results before formatting.
- Traversal is recursive and sorted by child name.
- Content search reads a file once per traversal entry and stores decoded lines temporarily.
- No persistent index exists; every search traverses the filesystem.

---

## Known Limitations

- No persistent index.
- No parallel traversal.
- DSL values cannot contain spaces.
- No path regex in DSL.
- No recursive `**` semantics.
- Content search reports first match per line only.
- Binary probe only checks first 4096 bytes.
- UTF-8 with replacement only.
- Regex filters are not sandboxed.
- Large text files are held as line lists during predicate evaluation.
- JSON/tree/sorted modes are not streaming.

---

## Design Patterns Used

- **Functional core, CLI shell**
- **Generator-based traversal**
- **Predicate protocol**
- **Composite pattern for AND/OR/NOT**
- **Recursive-descent parser**
- **Dataclass result models**
- **Per-entry cache**
- **Formatter strategy modules**
- **Explicit error hierarchy**

---

## Verification Summary

The repository documents a high coverage bar and CI execution on Python 3.11, 3.12, 3.13, and 3.14. CI installs the package with dev dependencies, runs Ruff, runs mypy on the library and tests, and runs pytest with coverage.

---

*Constitution reference: Article 4 (engineering quality), Article 6 (behavior verification), Article 7 (progressive complexity), and Article 8 (valid learner work).*

---


# Interface Design Specification
## App — File Search Tool
**Filesystem Utilities Group | Document 3 of 5**

---

## Public CLI Interface

### Console script

```powershell
file-search <root> [filters] [options]
```

### Module invocation

```powershell
python -m file_search_tool.cli <root> [filters] [options]
```

### Version

```powershell
file-search --version
```

---

## Positional Arguments

| Argument | Required | Description |
|---|---:|---|
| `root` | Yes | Root file or directory to search |

When the root is a directory, it is visited first and displayed as `.`. When the root is a file, only that file is searched and it also displays as `.`.

---

## CLI Filter Flags

| Flag | Type | Description |
|---|---|---|
| `--name` | glob | Match file or directory name |
| `--regex-name` | regex | Regex against file or directory name |
| `--path` | glob | Match normalized relative path |
| `--ext` | CSV | Match final suffix, such as `py,md,txt` |
| `--type` | choice | `file`, `dir`, or `symlink` |
| `--size` | expression | Size filter |
| `--modified-before` | date | Exclusive date boundary |
| `--modified-after` | date | Inclusive date boundary |
| `--modified-within` | duration | Modified within `3h`, `7d`, or `2w` |
| `--contains` | text | Plain text content search |
| `--contains-regex` | regex | Regex content search |
| `--query` | string | DSL query |

---

## CLI Traversal Flags

| Flag | Type | Description |
|---|---|---|
| `--depth` | int | Maximum traversal depth; root is depth 0 |
| `--exclude` | repeatable glob | Exclude pattern |
| `--all` | flag | Include hidden files and directories |
| `--follow-symlinks` | flag | Follow symlinked directories with cycle detection |
| `--ignore-case` | flag | Case-insensitive path/name/ext/exclude matching |
| `--case-sensitive` | flag | Explicit case-sensitive matching |
| `--content-ignore-case` | flag | Case-insensitive content search only |
| `--binary-error` | flag | Treat binary files as errors during content search |

---

## CLI Display Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--limit` | int | none | Maximum matched files |
| `--sort` | choice | none | `name`, `size`, or `mtime` |
| `--format` | choice | `plain` | `plain`, `tree`, or `json` |
| `--summary` | flag | false | Print summary to stderr |
| `--verbose` | flag | false | Print warnings to stderr |

---

## Query DSL Contract

### Fields

| Field | Meaning |
|---|---|
| `name:<glob>` | Name glob |
| `path:<glob>` | Relative path glob |
| `ext:<csv>` | Extension list |
| `type:file|dir|symlink` | Entry type |
| `size:<expr>` | Size expression |
| `modified:<expr>` | Modified-time expression |
| `contains:<text>` | Plain content text |

### Operators

```text
NOT > AND > OR
```

Operators are case-insensitive.

### Examples

```text
name:*.py AND size:>1KB AND NOT path:*/tests/*
(ext:py OR ext:md) AND modified:within:7d
contains:TODO
```

### DSL limitations

- Values cannot contain spaces.
- Content DSL is plain text, not regex.
- Invalid syntax exits with code `2` and uses `query error:`.

---

## Size Expression Contract

| Expression | Meaning |
|---|---|
| `1024` | exactly 1024 bytes |
| `1KB` | exactly 1024 bytes |
| `+10MB` | greater than 10 MiB |
| `>10MB` | greater than 10 MiB |
| `>=512B` | greater than or equal to 512 bytes |
| `-1KB` | less than 1 KiB |
| `<1KB` | less than 1 KiB |
| `<=1GB` | less than or equal to 1 GiB |
| `1KB..5MB` | inclusive range |

Units:
```text
B, KB, MB, GB, TB
```

---

## Modified-Time Contract

| Flag / DSL | Behavior |
|---|---|
| `--modified-before YYYY-MM-DD` | `mtime < local midnight` |
| `--modified-after YYYY-MM-DD` | `mtime >= local midnight` |
| `--modified-within 7d` | `mtime > now - 7 days` |
| `modified:before:YYYY-MM-DD` | DSL before |
| `modified:after:YYYY-MM-DD` | DSL after |
| `modified:within:7d` | DSL within |

Durations:
- `h` hours
- `d` days
- `w` weeks

---

## Output Contract

### Plain format

Path match:

```text
relative/path.txt
```

Content match:

```text
relative/path.txt:12: line text
```

Plain output streams lazily unless `--binary-error` requires buffering.

---

### JSON format

Always prints a JSON array.

No matches:

```json
[]
```

Result object includes:
- path
- relative_path
- type
- size
- mtime
- match_kind
- line_number
- line_text
- matched_text

---

### Tree format

Grouped by parent directory:

```text
src/
  main.py
  test.py:12: TODO
README.md
```

This is a flat grouped view, not a fully nested widget.

---

### Summary output

Printed to stderr:

```text
summary: files=... dirs=... matched_files=... content_matches=... entries_skipped=... permission_errors=... binary_skipped=... symlink_cycles=... elapsed=...s
```

Includes `stopped early` when a streaming or post-scan limit truncates results.

---

## Exit Codes

| Code | Meaning |
|---:|---|
| `0` | One or more matched files found |
| `1` | Search completed successfully with no matched files |
| `2` | Invalid input or expected `FileSearchError` |

Exit code is based on matched files, not individual content lines.

---

## Public Library Interface

### Imports

```python
from pathlib import Path
from file_search_tool import SearchOptions, search, search_with_stats
from file_search_tool.filters import NamePredicate
```

### `search()`

```python
search(root: Path, predicate=None, options=None) -> Iterator[SearchResult]
```

Returns results only.

### `search_with_stats()`

```python
search_with_stats(root, predicate=None, options=None, defer_limit=False) -> SearchSession
```

Returns:
- result iterator
- stats
- warnings

### Example

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

---

## Error Output Contract

DSL errors:

```text
query error: <message>
```

Other expected errors:

```text
error: <message>
```

---

## Environment Variables

None required.

---

## Configuration Files

### `pyproject.toml`

Defines:
- package metadata
- Python `>=3.11`
- zero runtime dependencies
- optional dev dependencies
- console script `file-search`
- pytest config
- coverage config
- Ruff config
- strict mypy config

### `.github/workflows/test.yml`

Runs:
- Python 3.11, 3.12, 3.13, 3.14
- Ruff
- mypy on library
- mypy on tests
- pytest with coverage

---

## Side Effects

| Operation | Side Effect |
|---|---|
| Search traversal | Reads filesystem metadata |
| Content search | Reads file content |
| Plain output | Writes matching rows to stdout |
| JSON/tree output | Collects matches then writes stdout |
| Summary | Writes counters to stderr |
| Verbose | Writes warnings to stderr |

The tool does not modify files.

---

*Constitution reference: Article 4 (input/output boundaries), Article 6 (verification), and Article 8 (understandable and verifiable work).*

---


# Runbook
## App — File Search Tool
**Filesystem Utilities Group | Document 4 of 5**

---

## Requirements

- Python 3.11+
- pip
- No runtime dependencies
- pytest/ruff/mypy for development

---

## Installation

### Runtime only

```powershell
python -m pip install -e .
```

### Development install

```powershell
python -m pip install -e ".[dev]"
```

### Lock-style test dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## Running the Tool

```powershell
file-search . --name "*.py"
```

Or:

```powershell
python -m file_search_tool.cli . --name "*.py"
```

---

## Smoke Tests

### Search for Python files

```powershell
file-search . --ext py
```

Expected:
- matching `.py` files on stdout
- exit code `0` if at least one match exists

---

### Search for text content

```powershell
file-search . --contains TODO
```

Expected content result format:

```text
path/to/file.py:12: # TODO: ...
```

---

### No-match behavior

```powershell
file-search . --name "definitely-not-present-*"
```

Expected:
- no stdout
- exit code `1`

---

## Running Tests

```powershell
python -m pytest --cov=file_search_tool --cov-report=term-missing
```

---

## Running Quality Checks

```powershell
ruff check file_search_tool tests
mypy file_search_tool
mypy tests --disable-error-code=no-untyped-def --disable-error-code=no-untyped-call
```

---

## Standard Operating Procedures

### Find by name

```powershell
file-search . --name "*.md"
```

---

### Find by extension

```powershell
file-search . --ext py,md
```

---

### Find by content

```powershell
file-search . --contains TODO
```

Case-insensitive content only:

```powershell
file-search . --contains todo --content-ignore-case
```

Regex content:

```powershell
file-search . --contains-regex "TODO|FIXME"
```

---

### Use DSL query

```powershell
file-search . --query "name:*.py AND size:>1KB AND NOT path:*/tests/*"
```

---

### Combine flags and DSL

```powershell
file-search . --name "*.py" --query "contains:TODO"
```

This behaves as:

```text
name:*.py AND contains:TODO
```

---

### Include hidden files

```powershell
file-search . --all --name ".env"
```

---

### Exclude directories or files

```powershell
file-search . --exclude ".git" --exclude "__pycache__"
```

---

### Follow symlinks

```powershell
file-search . --follow-symlinks
```

Cycle detection prevents re-descending the same directory identity.

---

### Sort output

```powershell
file-search . --ext py --sort name
file-search . --ext py --sort size
file-search . --ext py --sort mtime
```

Sorting collects results before output.

---

### Use JSON output

```powershell
file-search . --contains TODO --format json
```

---

### Use grouped tree output

```powershell
file-search . --ext py --format tree
```

---

### Print summary stats

```powershell
file-search . --contains TODO --summary
```

Stats are printed to stderr.

---

### Treat binary files as errors

```powershell
file-search . --contains TODO --binary-error
```

Plain output is buffered in this mode so partial results are not printed before a binary error.

---

## Health Checks

### Package import

```powershell
python -c "from file_search_tool import search_with_stats; print(search_with_stats)"
```

---

### CLI entry point

```powershell
file-search --version
```

Expected:

```text
file-search 0.1.3
```

or an installed package version.

---

### Basic traversal

```powershell
file-search . --summary
```

Expected:
- root appears as `.` when no filters exclude it
- summary stats print to stderr

---

### JSON validity

```powershell
file-search . --name "definitely-not-present" --format json
```

Expected stdout:

```json
[]
```

Expected exit code:

```text
1
```

---

## Known Failure Modes

### Root does not exist

**Trigger:**

```powershell
file-search missing-dir
```

**Expected:**

```text
error: root path does not exist: missing-dir
```

Exit code:
```text
2
```

---

### Invalid DSL query

**Trigger:**

```powershell
file-search . --query "name:*.py contains:TODO"
```

**Expected:**

```text
query error: expected AND/OR before 'contains'
```

---

### Empty extension list

**Trigger:**

```powershell
file-search . --ext ,,
```

**Expected:**

```text
error: extension list cannot be empty
```

---

### Empty content search

**Trigger:** library caller or CLI passes empty content pattern.

**Expected:**

```text
content search pattern cannot be empty
```

---

### Binary file during content search

Default behavior:
- binary file is skipped
- summary increments `binary_skipped`

With `--binary-error`:
- expected error
- exit code `2`

---

### Regex performance problem

**Trigger:** pathological regex on large files.

**Resolution:** Use trusted regex patterns only; prefer plain `--contains` for simple strings.

---

### Hidden files missing from results

**Trigger:** hidden entries skipped by default.

**Resolution:** add `--all`.

---

### Limit differs across formats

**Observation:**
- plain + limit stops traversal early
- sort/json/tree scan fully first, then apply limit

**Resolution:** compare summary stats only with this difference in mind.

---

## Troubleshooting Decision Tree

```text
Search failed
  ├── Exit code 2?
  │   ├── Check stderr prefix: query error vs error
  │   ├── Validate root exists
  │   ├── Validate DSL syntax
  │   ├── Validate size/date expressions
  │   └── Check binary-error behavior
  ├── No matches?
  │   ├── Check hidden files; add --all
  │   ├── Check case sensitivity
  │   ├── Check extension uses final suffix only
  │   ├── Check exclude patterns
  │   └── Run with --summary
  ├── Content not shown?
  │   ├── Confirm --contains or --contains-regex
  │   ├── Check binary skip count
  │   ├── Check encoding expectations
  │   └── Remember one match per line
  └── Output memory high?
      ├── Avoid --sort
      ├── Avoid --format json/tree for large trees
      └── Use plain streaming output
```

---

## Dependency Failure Handling

### CLI command not found

Install editable:

```powershell
python -m pip install -e .
```

---

### Dev tools missing

Install dev dependencies:

```powershell
python -m pip install -e ".[dev]"
```

---

### CI mismatch locally

Run:

```powershell
ruff check file_search_tool tests
mypy file_search_tool
mypy tests --disable-error-code=no-untyped-def --disable-error-code=no-untyped-call
python -m pytest --cov=file_search_tool --cov-report=term-missing -q
```

---

## Recovery Procedures

### Recover from bad query

1. Remove `--query`.
2. Rebuild using flags.
3. Add DSL terms one at a time.
4. Insert explicit `AND` or `OR` between filters.
5. Use parentheses when precedence is unclear.

---

### Recover from too many results

1. Add `--type file`.
2. Add `--ext` or `--name`.
3. Add `--exclude` for noisy directories.
4. Add `--depth`.
5. Add `--limit`.

---

### Recover from missing hidden files

Use:

```powershell
file-search . --all ...
```

---

### Recover from binary failures

Remove `--binary-error`, or narrow the search to known text files with `--ext` or `--name`.

---

## Maintenance Notes

- Keep core library free of CLI imports.
- Keep runtime dependencies empty unless documented by a new decision.
- Keep traversal stats synchronized with output mode behavior.
- Add tests before changing DSL grammar.
- Add tests before changing limit semantics.
- Preserve exit code meanings.
- Do not reuse `SearchSession` or predicate instances across concurrent searches.
- Document any future indexing or parallel traversal separately.

---

*Constitution reference: Article 6 (behavior verification), Article 5 (constraints and trade-offs), and Article 8 (verifiable learner work).*

---


# Lessons Learned
## App — File Search Tool
**Filesystem Utilities Group | Document 5 of 5**

---

## Why This Design Was Chosen

This design was chosen because a file search tool is a strong exercise in Python systems programming. It touches filesystem traversal, metadata handling, generator design, predicate composition, CLI parsing, text processing, error handling, output formatting, and testable boundaries.

The library/CLI split is the key architectural choice. A CLI-only implementation would work, but it would make the search engine harder to reuse and harder to test. A library-first design keeps the core behavior available to Python callers while allowing the CLI to focus on argument parsing, formatting, and exit codes.

The predicate system is the second important choice. It allows `--name`, `--ext`, `--contains`, and DSL expressions to share the same evaluation model. Instead of writing separate search paths for flags and queries, everything compiles into a predicate tree.

---

## What Was Intentionally Omitted

**Persistent index:** Every search walks the filesystem. This keeps behavior fresh and avoids index corruption or staleness problems.

**Parallel traversal:** Simpler single-threaded traversal is easier to reason about and test.

**External grep engine:** Content search is implemented in Python to preserve the learning value.

**Full query language:** The DSL supports useful composition but omits quoting, spaces in values, path regex fields, and advanced grouping syntax beyond parentheses.

**Binary search:** The tool is designed for text content search.

**Encoding detection:** UTF-8 with replacement is predictable and avoids a dependency.

**Full recursive glob semantics:** `fnmatch` behavior is documented instead of implementing custom globstar behavior.

---

## Biggest Weakness

The biggest weakness is that the tool has no persistent index. It is correct and simple for local searches, but repeated searches over very large directory trees will repeatedly traverse and stat the same files.

The second weakness is the DSL. It is intentionally small, but the inability to quote values with spaces limits content queries. Users must use CLI flags when search text includes spaces.

The third weakness is content-search memory behavior. A file is read into a list of lines for the duration of predicate evaluation. This is reasonable for normal local text files but not ideal for very large logs.

---

## Scaling Considerations

**If search volume grows:**
- Add optional indexing.
- Track file mtimes and sizes for incremental updates.
- Add cache invalidation rules.
- Decide whether index storage belongs in SQLite or a custom file format.

**If huge trees are common:**
- Add parallel traversal carefully.
- Make warning/stats updates thread-safe.
- Avoid sorting unless requested.
- Keep streaming output as the default.

**If huge text files are common:**
- Stream content line-by-line where possible.
- Design a way for multiple content predicates to share line scans without holding the whole file.
- Add explicit max file size options.

**If DSL expands:**
- Add quoted strings.
- Add escaped characters.
- Add regex fields carefully.
- Preserve clear syntax errors.

---

## What the Next Refactor Would Be

1. **Quoted DSL values** — allow `contains:"hello world"` without falling back to CLI flags.

2. **Optional max file size for content scanning** — protect searches against accidentally reading huge files.

3. **Streaming multi-content evaluation** — reduce memory pressure for very large text files.

4. **More explicit output schema versioning** — useful if JSON output becomes consumed by other tools.

5. **Optional index experiment** — only after documenting freshness and invalidation rules.

---

## What This Project Taught

- **Traversal is more than recursion.** Hidden files, symlinks, cycles, permission errors, root display, depth limits, and stats all matter.

- **Predicate composition is powerful.** Once filters share a protocol, CLI flags and DSL queries become different front ends over the same engine.

- **Streaming and formatting pull in different directions.** Plain output can stream, but JSON, tree, sorting, and deferred limits require collection.

- **Content search introduces state.** Multiple predicates need shared decoded lines, but that cache must be scoped carefully.

- **CLI contracts matter.** Exit codes, stderr prefixes, summary behavior, and JSON empty-array behavior are part of the product.

- **Small DSLs still need real parsers.** Precedence, parentheses, empty values, glued fields, and adjacent filters all require careful error messages.

- **Limit semantics must be documented.** A streaming limit and post-scan limit are both valid, but users need to know which mode they are in.

---

*Constitution v2.0 checklist: This document satisfies Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity) for File Search Tool.*
