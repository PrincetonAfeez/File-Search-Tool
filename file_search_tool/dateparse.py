"""Date and duration parsing for modified-time filters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
import re

from file_search_tool.errors import InvalidDateExpression


DURATION_RE = re.compile(r"^\s*(?P<number>\d+)(?P<unit>[hdw])\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ModifiedTimeFilter:
    operator: str
    timestamp: float

    def matches(self, mtime: float | None) -> bool:
        if mtime is None:
            return False
        if self.operator == "before":
            return mtime < self.timestamp
        if self.operator == "after":
            return mtime >= self.timestamp
        if self.operator == "within":
            return mtime > self.timestamp
        raise InvalidDateExpression(f"unknown modified-time operator: {self.operator}")


def local_midnight_timestamp(date_text: str) -> float:
    if not date_text.strip():
        raise InvalidDateExpression("empty date expression")
    try:
        date_value = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise InvalidDateExpression(f"invalid date: {date_text}") from exc
    local_zone = datetime.now().astimezone().tzinfo
    return datetime.combine(date_value, time.min, tzinfo=local_zone).timestamp()


def duration_to_timedelta(duration: str) -> timedelta:
    if not duration.strip():
        raise InvalidDateExpression("empty duration expression")
    match = DURATION_RE.match(duration)
    if not match:
        raise InvalidDateExpression(f"invalid duration: {duration}")
    number = int(match.group("number"))
    unit = match.group("unit").lower()
    if unit == "h":
        return timedelta(hours=number)
    if unit == "d":
        return timedelta(days=number)
    if unit == "w":
        return timedelta(weeks=number)
    raise InvalidDateExpression(f"invalid duration unit: {unit}")


def modified_before(date_text: str) -> ModifiedTimeFilter:
    return ModifiedTimeFilter("before", local_midnight_timestamp(date_text))


def modified_after(date_text: str) -> ModifiedTimeFilter:
    return ModifiedTimeFilter("after", local_midnight_timestamp(date_text))


def modified_within(duration: str, now: datetime | None = None) -> ModifiedTimeFilter:
    current = now or datetime.now().astimezone()
    cutoff = current - duration_to_timedelta(duration)
    return ModifiedTimeFilter("within", cutoff.timestamp())


def parse_modified_expression(text: str) -> ModifiedTimeFilter:
    expr = text.strip()
    if expr.startswith("before:"):
        return modified_before(expr.removeprefix("before:"))
    if expr.startswith("after:"):
        return modified_after(expr.removeprefix("after:"))
    if expr.startswith("within:"):
        return modified_within(expr.removeprefix("within:"))
    raise InvalidDateExpression(
        "modified expressions must use before:YYYY-MM-DD, after:YYYY-MM-DD, or within:7d"
    )

