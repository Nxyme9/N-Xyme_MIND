"""Structured JSON logger with rotation."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "context"):
            log_entry["context"] = record.context

        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_entry, default=str)


class ContextLogger(logging.Logger):
    """Logger that accepts context keyword arguments."""

    def _log(
        self,
        level: int,
        msg: object,
        args: Any,
        exc_info: Any = None,
        extra: dict[str, Any] | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
    ) -> None:
        if extra is None:
            extra = {}
        if "context" not in extra:
            context = {}
        else:
            context = extra.pop("context")
        if context:
            extra["context"] = context
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


logging.setLoggerClass(ContextLogger)


def get_logger(name: str) -> ContextLogger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def setup_logging(
    log_dir: Path | None = None,
    level: int = logging.DEBUG,
    max_bytes: int = 100 * 1024 * 1024,
    backup_count: int = 7,
    console: bool = True,
) -> logging.Logger:
    """Configure structured JSON logging with rotation.

    Args:
        log_dir: Directory to store log files. Defaults to project root/logs.
        level: Minimum log level.
        max_bytes: Maximum log file size before rotation (default 100MB).
        backup_count: Number of rotated files to keep (default 7 days).
        console: Enable console output for development.

    Returns:
        Root logger instance.
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    json_formatter = JSONFormatter()

    log_file = log_dir / "delegation.log"
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    return root_logger
