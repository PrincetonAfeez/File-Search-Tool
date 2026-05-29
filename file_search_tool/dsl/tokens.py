"""Token definitions for the query DSL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    position: int

