"""CLI diagnostic output backed by logging."""

from __future__ import annotations

import logging
from typing import TextIO

logger = logging.getLogger("file_search_tool")


def emit_stderr(message: str, stderr: TextIO) -> None:
    """Write a user-facing diagnostic line to stderr and log it at debug level."""

    logger.debug(message)
    print(message, file=stderr)


def emit_warning(warning: str, stderr: TextIO) -> None:
    """Write a warning line to stderr and log it at debug level."""

    emit_stderr(f"warning: {warning}", stderr)
