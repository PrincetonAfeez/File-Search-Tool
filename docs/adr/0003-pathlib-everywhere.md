# ADR 0003: pathlib Everywhere

## Decision

Use `pathlib.Path` throughout the core.

## Reason

Path objects make filesystem operations clearer and avoid fragile string path
manipulation.

## Tradeoff

Some formatting still requires converting paths to strings at the boundary.
