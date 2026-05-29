# ADR 0004: Small Query DSL Over Flags Only

## Decision

Add a lightweight query language with AND, OR, NOT, and field:value filters.

## Reason

The DSL teaches tokenization, parsing, AST design, and predicate evaluation. It
also makes complex searches easier to express.

## Tradeoff

A DSL adds parsing complexity. CLI flags remain available for simple use cases.
