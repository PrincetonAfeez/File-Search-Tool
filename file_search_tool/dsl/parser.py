"""Recursive-descent parser for the query DSL."""

from __future__ import annotations

import re

from file_search_tool.dsl.ast import AndNode, FilterNode, NotNode, OrNode
from file_search_tool.dsl.lexer import lex
from file_search_tool.dsl.tokens import Token
from file_search_tool.errors import QuerySyntaxError

_GLUED_DSL_FIELD = re.compile(
    r"(?<=[^\s:])(?P<field>name|path|ext|type|size|modified|contains):",
    re.IGNORECASE,
)


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current()
        self.index += 1
        return token

    def expect(self, token_type: str, message: str) -> Token:
        if self.current().type != token_type:
            raise QuerySyntaxError(message)
        return self.advance()

    def parse(self) -> object:
        if self.current().type == "EOF":
            raise QuerySyntaxError("empty query")
        node = self.parse_or()
        if self.current().type != "EOF":
            token = self.current()
            if token.type in {"NOT", "LPAREN"}:
                raise QuerySyntaxError("expected AND/OR between filters near ...")
            raise QuerySyntaxError(f"unexpected token: {token.value}")
        return node

    def parse_or(self) -> object:
        node = self.parse_and()
        while self.current().type == "OR":
            self.advance()
            node = OrNode(node, self.parse_and())
        return node

    def parse_and(self) -> object:
        node = self.parse_not()
        while self.current().type == "AND":
            self.advance()
            node = AndNode(node, self.parse_not())
        return node

    def parse_not(self) -> object:
        if self.current().type == "NOT":
            self.advance()
            return NotNode(self.parse_not())
        return self.parse_primary()

    def parse_primary(self) -> object:
        if self.current().type == "LPAREN":
            self.advance()
            node = self.parse_or()
            self.expect("RPAREN", "unmatched '('")
            return node
        return self.parse_filter()

    def _looks_like_adjacent_filter(self) -> bool:
        if self.current().type != "WORD":
            return False
        next_index = self.index + 1
        return next_index < len(self.tokens) and self.tokens[next_index].type == "COLON"

    def parse_filter(self) -> FilterNode:
        field = self.expect("WORD", "expected field name").value
        self.expect("COLON", f"expected ':' after field '{field}'")

        value_parts: list[str] = []
        while self.current().type not in {"EOF", "AND", "OR", "RPAREN", "NOT", "LPAREN"}:
            if value_parts and self._looks_like_adjacent_filter():
                break
            value_parts.append(self.advance().value)

        value = "".join(value_parts)
        if not value:
            raise QuerySyntaxError(f"missing value for field '{field}'")

        glued = _GLUED_DSL_FIELD.search(value)
        if glued is not None:
            raise QuerySyntaxError(f"expected AND/OR before '{glued.group('field')}'")

        token = self.current()
        if token.type in {"WORD", "NOT", "LPAREN"}:
            raise QuerySyntaxError(f"expected AND/OR before '{token.value}'")
        return FilterNode(field.lower(), value)


def parse_query(query: str) -> object:
    return Parser(lex(query)).parse()

