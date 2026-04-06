"""Tests for structured JSON logger."""

import json
import logging
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tools.observability.logger import (
    JSONFormatter,
    ContextLogger,
    get_logger,
    setup_logging,
)


class TestJSONFormatter:
    def test_basic_format(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert data["module"] == "test"
        assert data["function"] is None
        assert data["line"] == 10
        assert "timestamp" in data

    def test_exception_format(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="something failed",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "ERROR"
        assert data["message"] == "something failed"
        assert "exception" in data
        assert "ValueError: test error" in data["exception"]

    def test_context_format(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=30,
            msg="with context",
            args=(),
            exc_info=None,
        )
        record.context = {"task_id": "123", "agent": "hephaestus"}
        result = formatter.format(record)
        data = json.loads(result)

        assert data["context"] == {"task_id": "123", "agent": "hephaestus"}


class TestContextLogger:
    def test_context_logger_type(self):
        logger = get_logger("test.context")
        assert isinstance(logger, ContextLogger)

    def test_context_logger_logs(self, caplog):
        logger = get_logger("test.context.logs")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

        logger.info("test message", extra={"context": {"key": "value"}})

        assert len(caplog.records) == 1
        assert caplog.records[0].message == "test message"


class TestSetupLogging:
    def test_setup_logging_creates_log_dir(self, tmp_path):
        log_dir = tmp_path / "custom_logs"
        setup_logging(log_dir=log_dir, console=False)

        assert log_dir.exists()
        assert (log_dir / "delegation.log").exists()

    def test_setup_logging_handlers(self, tmp_path):
        log_dir = tmp_path / "test_handlers"
        logger = setup_logging(log_dir=log_dir, console=True)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "TimedRotatingFileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_setup_logging_no_console(self, tmp_path):
        log_dir = tmp_path / "no_console"
        logger = setup_logging(log_dir=log_dir, console=False)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" not in handler_types
        assert "TimedRotatingFileHandler" in handler_types

    def test_setup_logging_level(self, tmp_path):
        log_dir = tmp_path / "level_test"
        logger = setup_logging(log_dir=log_dir, level=logging.WARNING, console=False)

        assert logger.level == logging.WARNING

    def test_log_output_is_json(self, tmp_path):
        log_dir = tmp_path / "json_test"
        setup_logging(log_dir=log_dir, console=False)

        logger = get_logger("json_test")
        logger.info("test json output")

        log_file = log_dir / "delegation.log"
        content = log_file.read_text().strip()
        lines = content.split("\n")

        for line in lines:
            if line.strip():
                data = json.loads(line)
                assert "timestamp" in data
                assert "level" in data
                assert "message" in data
