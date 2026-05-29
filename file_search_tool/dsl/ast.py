"""AST nodes for the query DSL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilterNode:
    field: str
    value: str


@dataclass(frozen=True)
class AndNode:
    left: object
    right: object


@dataclass(frozen=True)
class OrNode:
    left: object
    right: object


@dataclass(frozen=True)
class NotNode:
    node: object

