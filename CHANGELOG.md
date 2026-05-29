# Changelog

All notable changes to this project are documented in this file.

## 0.1.3 — 2026-05-29

### Fixed

- Reject empty `--modified-before`, `--modified-after`, and `--modified-within`
  values with exit code 2
- Case-insensitive literal regex content search uses Unicode casefold matching
  (fixes `groß` / `gross` with `--contains-regex`)
- Reject DSL filter values glued without whitespace (for example
  `name:*.pyNOTcontains:TODO`)
- Sort `--sort size` / `--sort mtime` places directories after files

### Changed

- Content search reads text line-by-line after a binary probe instead of
  `read_bytes()` + decode
- Summary output includes `symlink_cycles` counter
- Move scope planning documents to `docs/scope/`

### Documentation

- Update test count to 217; add Known Limitations section; remove unimplemented
  web-layer promise; document duration granularity and sort order

## 0.1.2 — 2026-05-29

### Fixed

- `--summary` no longer corrupts JSON output; summary now writes to stderr
- `stopped early` summary line only appears when `--limit` actually truncated
  results
- DSL rejects adjacent filters without `AND`/`OR` (e.g.
  `name:*.py NOT contains:TODO`)
- `OrPredicate` deduplicates content matches by line number, no more duplicate
  output rows
- Case-insensitive `--contains` preserves the original `matched_text` (handles
  ß↔ss boundary)
- `--query ""`, `--name ""`, `--path ""`, `--regex-name ""`, `--contains-regex ""`,
  `--modified-before/after/within ""` all exit 2 with a clear error
- `entries_skipped` no longer double-counts mid-content-read failures (kept under
  `permission_errors`)

### Changed

- `_count_matched_files` consolidated as the public helper
  `count_unique_matched_files`
- `__main__.py` guarded with `if __name__ == "__main__":`
- ADRs 0003 (pathlib), 0004 (DSL), 0005 (library-core) added

### Documentation

- Expand README with features overview, requirements, project layout, and quality
  metrics (99% library coverage; test count tracked via CI badge)
- Remove the CI badge placeholder note now that repository URLs are set
- Document development workflow: editable install, lint, type-check, and coverage

### Packaging

- Add project keywords and GitHub URLs to `pyproject.toml`
- Align `requirements.txt` header with the `dev` optional dependency group
- Ignore lint/type-check caches, OS artifacts, and local editor files in
  `.gitignore`

## 0.1.1 — 2026-05-28

### Fixed

- Reject empty content search patterns instead of matching every line
- Reject empty extension lists consistently in CLI flags and DSL `ext:` filters
- Report DSL `size:`/`modified:` parse failures with the `query error:` prefix
- Clarify the `--binary-error` message (binary file not searchable)
- Clear per-entry content caches for non-matching entries so the match cache no
  longer grows unbounded across a traversal

### Changed

- Add public `SearchStats.record_binary_skip()` instead of touching private state
- Annotate `compile_ast()` return type as `BasePredicate`
- Share a per-entry `ContentReadCache` so multiple `AND`/`OR` content filters read
  each file once per traversal step instead of re-reading it per predicate
- Adopt the `Predicate` protocol as the public engine interface and drop a dead
  `None` filter in `combine_with_and()`
- Add `ruff` and `mypy --strict` to dev dependencies and CI
- Add `--version` flag to the CLI

### Documentation

- Document DSL operator precedence, case-insensitive operators, empty JSON
  output, and `--summary` scan-counter behavior under `--limit`
- Document root-entry name/path matching, `Path.suffix`-only extension matching,
  and the unselectable `other` entry type
- Document exact-size `--size` syntax, modified-time boundary semantics,
  duration units (`h`/`d`/`w`), and single-use predicate/session threading rules

### Tests

- Cover traversal error paths (permission errors, `iterdir` `OSError`,
  `stat`→`lstat` fallback, fully unreadable entries)
- Add a `python -m file_search_tool` entry-point smoke test
- Expand coverage for date/size parsing, CLI sort/tree/version paths, options
  wiring, utils helpers, symlink-cycle identity handling, and file-limit logic
- Grow the suite to 189 tests with 99% library coverage across CLI, DSL,
  predicates, formatters, and traversal

### Performance

- Use a set for O(n) file limiting in sorted/JSON/tree output

### Polish

- Wire `sort_key_text()` into name sorting; unify CLI flag access in `options.py`
- Add CI badge, Python 3.14 matrix entry, and mypy coverage for tests

## 0.1.0 — 2026-05-27

### Added

- Recursive file search library and `file-search` CLI
- Composable predicates with a small boolean query DSL
- Content search with plain and regex modes
- Plain, JSON, and grouped tree output formats
- GitHub Actions CI on Python 3.11–3.13
- MIT license

### Fixed

- OR/content boolean semantics and per-file `--limit` behavior
- Summary stats alignment after sorted or limited output
- Symlink cycle duplicate directory emission
- Binary skip counting, traversal/content error reporting, and CLI exit codes

### Documentation

- README query semantics, summary fields, and known limitations
- Architecture decision records under `docs/adr/`
