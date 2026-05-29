"""Lexer for the small query DSL."""

from __future__ import annotations

from file_search_tool.dsl.tokens import Token
from file_search_tool.errors import QuerySyntaxError


def lex(query: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    while index < len(query):
        char = query[index]
        if char.isspace():
            index += 1
            continue
        if char == "(":
            tokens.append(Token("LPAREN", char, index))
            index += 1
            continue
        if char == ")":
            tokens.append(Token("RPAREN", char, index))
            index += 1
            continue
        if char == ":":
            tokens.append(Token("COLON", char, index))
            index += 1
            continue

        start = index
        while index < len(query) and not query[index].isspace() and query[index] not in "():":
            index += 1
        value = query[start:index]
        if not value:
            raise QuerySyntaxError(f"unexpected character at position {index}")
        upper = value.upper()
        token_type = upper if upper in {"AND", "OR", "NOT"} else "WORD"
        tokens.append(Token(token_type, value, start))

    tokens.append(Token("EOF", "", len(query)))
    return tokens

