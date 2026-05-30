# Schema

Simple JSON Schema files for the File Search Tool repository.

These schemas document the public data contracts used by the library and CLI JSON output.
They are intentionally lightweight and portfolio-friendly rather than a generated API specification.

## Files

- `search-result.schema.json` — one emitted search result object.
- `search-results.schema.json` — CLI `--format json` array output.
- `search-stats.schema.json` — summary/statistics counters.
- `file-entry.schema.json` — internal traversal entry shape exposed to predicates/results.
- `search-options.schema.json` — library search option contract.
- `cli-display-options.schema.json` — CLI display/formatting option contract.
- `search-session.schema.json` — search session object shape.
- `content-match.schema.json` — one content match line.
- `schema-index.json` — machine-readable index of all schema files.

## Notes

- JSON output is an array of `SearchResult` objects.
- `relative_path` is the primary stable user-facing path field.
- `path` may be absolute or platform-specific depending on caller context.
- `mtime` is a Unix timestamp when available.
- Content-only fields are nullable for path matches.
