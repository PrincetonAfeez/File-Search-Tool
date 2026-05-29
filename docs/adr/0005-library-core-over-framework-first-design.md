# ADR 0005: Library Core Over Framework-First Design

## Decision

Build the search engine as a pure Python library and keep CLI/web as adapters.

## Reason

The search logic should be reusable and testable without a framework. This proves
clean separation of concerns.

## Tradeoff

The CLI and web layer need small adapter code, but the core remains portable.
