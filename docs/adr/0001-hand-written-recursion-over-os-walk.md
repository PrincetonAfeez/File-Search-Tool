# ADR 0001: Hand-Written Recursion Over os.walk

## Decision

The project implements recursive traversal directly instead of using `os.walk`.

## Reason

The main learning goal is to understand recursive filesystem traversal, depth
control, exclusions, permission handling, and symlink behavior.

## Tradeoff

`os.walk` is shorter and battle-tested. The custom traversal needs tests and
careful error handling.

