"""Project-specific exceptions."""


class FileSearchError(Exception):
    """Base class for expected file-search errors."""


class TraversalError(FileSearchError):
    """Raised when traversal cannot start or continue safely."""


class QuerySyntaxError(FileSearchError):
    """Raised when a DSL query cannot be parsed."""


class InvalidSizeExpression(FileSearchError):
    """Raised when a size expression is invalid."""


class InvalidDateExpression(FileSearchError):
    """Raised when a date expression is invalid."""


class InvalidFilterError(FileSearchError):
    """Raised when a filter cannot be created."""


class ContentSearchError(FileSearchError):
    """Raised when content search cannot be configured."""


class CLIError(FileSearchError):
    """Raised for command-line input errors."""

