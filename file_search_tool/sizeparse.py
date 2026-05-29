"""Human-friendly size expression parsing."""

from __future__ import annotations

from dataclasses import dataclass
import re

from file_search_tool.errors import InvalidSizeExpression


UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
}


SIZE_RE = re.compile(r"^\s*(?P<number>\d+(?:\.\d+)?)(?P<unit>B|KB|MB|GB|TB)?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class SizeFilter:
    operator: str
    left: int
    right: int | None = None

    def matches(self, size: int | None) -> bool:
        if size is None:
            return False
        if self.operator == "eq":
            return size == self.left
        if self.operator == "gt":
            return size > self.left
        if self.operator == "gte":
            return size >= self.left
        if self.operator == "lt":
            return size < self.left
        if self.operator == "lte":
            return size <= self.left
        if self.operator == "range":
            return self.right is not None and self.left <= size <= self.right
        raise InvalidSizeExpression(f"unknown size operator: {self.operator}")


def parse_size_value(text: str) -> int:
    match = SIZE_RE.match(text)
    if not match:
        raise InvalidSizeExpression(f"invalid size value: {text}")
    number = float(match.group("number"))
    unit = (match.group("unit") or "B").upper()
    if unit not in UNITS:
        raise InvalidSizeExpression(f"invalid size unit: {unit}")
    return int(number * UNITS[unit])


def parse_size_expression(text: str) -> SizeFilter:
    expr = text.strip()
    if not expr:
        raise InvalidSizeExpression("empty size expression")

    if ".." in expr:
        left, right = expr.split("..", 1)
        if not left or not right:
            raise InvalidSizeExpression(f"invalid size range: {text}")
        left_size = parse_size_value(left)
        right_size = parse_size_value(right)
        if left_size > right_size:
            raise InvalidSizeExpression(f"invalid size range: {text}")
        return SizeFilter("range", left_size, right_size)

    for prefix, operator in (
        (">=", "gte"),
        ("<=", "lte"),
        (">", "gt"),
        ("<", "lt"),
        ("+", "gt"),
        ("-", "lt"),
    ):
        if expr.startswith(prefix):
            value = expr[len(prefix) :]
            if not value:
                raise InvalidSizeExpression(f"missing size value: {text}")
            return SizeFilter(operator, parse_size_value(value))

    return SizeFilter("eq", parse_size_value(expr))

