"""Test the DSL lexer."""

from file_search_tool.dsl.lexer import lex


def test_lexer_tokenizes_boolean_query():
    tokens = lex("name:*.py AND NOT path:*/tests/*")

    assert [token.type for token in tokens[:-1]] == [
        "WORD",
        "COLON",
        "WORD",
        "AND",
        "NOT",
        "WORD",
        "COLON",
        "WORD",
    ]

