"""Tests for CLI diagnostic logging helpers."""

from io import StringIO
import logging

from file_search_tool.diagnostics import emit_stderr, emit_warning


def test_emit_stderr_logs_and_prints(caplog):
    stderr = StringIO()

    with caplog.at_level(logging.DEBUG, logger="file_search_tool"):
        emit_stderr("error: bad flag", stderr)

    assert stderr.getvalue() == "error: bad flag\n"
    assert "error: bad flag" in caplog.text


def test_emit_warning_prefixes_message(caplog):
    stderr = StringIO()

    with caplog.at_level(logging.DEBUG, logger="file_search_tool"):
        emit_warning("binary file skipped: data.bin", stderr)

    assert stderr.getvalue() == "warning: binary file skipped: data.bin\n"
    assert "warning: binary file skipped: data.bin" in caplog.text
