"""Compile DSL AST nodes into search predicates."""

from __future__ import annotations

from file_search_tool.dateparse import parse_modified_expression
from file_search_tool.dsl.ast import AndNode, FilterNode, NotNode, OrNode
from file_search_tool.errors import (
    InvalidDateExpression,
    InvalidFilterError,
    InvalidSizeExpression,
    QuerySyntaxError,
)
from file_search_tool.filters import (
    AndPredicate,
    ContentPredicate,
    ExtensionPredicate,
    ModifiedTimePredicate,
    NamePredicate,
    NotPredicate,
    OrPredicate,
    PathPredicate,
    Predicate,
    SizePredicate,
    TypePredicate,
)
from file_search_tool.sizeparse import parse_size_expression
from file_search_tool.utils import split_csv_values


def compile_ast(
    node: object,
    *,
    case_sensitive: bool = True,
    content_case_sensitive: bool | None = None,
    binary_policy: str = "skip",
) -> Predicate:
    content_sensitive = case_sensitive if content_case_sensitive is None else content_case_sensitive

    if isinstance(node, FilterNode):
        field = node.field
        value = node.value
        if field == "name":
            return NamePredicate(value, case_sensitive=case_sensitive)
        if field == "path":
            return PathPredicate(value, case_sensitive=case_sensitive)
        if field == "ext":
            try:
                return ExtensionPredicate(split_csv_values(value), case_sensitive=case_sensitive)
            except InvalidFilterError as exc:
                raise QuerySyntaxError(str(exc)) from exc
        if field == "type":
            if value not in {"file", "dir", "symlink"}:
                raise QuerySyntaxError(f"unknown type: {value}")
            return TypePredicate(value)
        if field == "size":
            try:
                return SizePredicate(parse_size_expression(value))
            except InvalidSizeExpression as exc:
                raise QuerySyntaxError(str(exc)) from exc
        if field == "modified":
            try:
                return ModifiedTimePredicate(parse_modified_expression(value))
            except InvalidDateExpression as exc:
                raise QuerySyntaxError(str(exc)) from exc
        if field == "contains":
            return ContentPredicate(value, case_sensitive=content_sensitive, binary_policy=binary_policy)
        raise QuerySyntaxError(f"unknown field '{field}'")

    if isinstance(node, AndNode):
        return AndPredicate(
            [
                compile_ast(
                    node.left,
                    case_sensitive=case_sensitive,
                    content_case_sensitive=content_case_sensitive,
                    binary_policy=binary_policy,
                ),
                compile_ast(
                    node.right,
                    case_sensitive=case_sensitive,
                    content_case_sensitive=content_case_sensitive,
                    binary_policy=binary_policy,
                ),
            ]
        )
    if isinstance(node, OrNode):
        return OrPredicate(
            [
                compile_ast(
                    node.left,
                    case_sensitive=case_sensitive,
                    content_case_sensitive=content_case_sensitive,
                    binary_policy=binary_policy,
                ),
                compile_ast(
                    node.right,
                    case_sensitive=case_sensitive,
                    content_case_sensitive=content_case_sensitive,
                    binary_policy=binary_policy,
                ),
            ]
        )
    if isinstance(node, NotNode):
        return NotPredicate(
            compile_ast(
                node.node,
                case_sensitive=case_sensitive,
                content_case_sensitive=content_case_sensitive,
                binary_policy=binary_policy,
            )
        )

    raise QuerySyntaxError("unsupported query node")
