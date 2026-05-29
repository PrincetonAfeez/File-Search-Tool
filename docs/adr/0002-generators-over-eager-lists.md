# ADR 0002: Generators Over Eager Lists

## Decision

Traversal and plain search output use generators.

## Reason

Generators let results appear early, reduce memory use, and allow `--limit` to
stop traversal before the full tree is scanned.

## Tradeoff

Sorting, tree output, and JSON arrays collect results before formatting.

