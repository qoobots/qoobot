"""
brain_ai/utils/logging.py — Structured logging setup for brain_ai.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    service_name: str = "brain_ai",
) -> None:
    """
    Configure root logger for brain_ai.

    Args:
        level:        Log level string (DEBUG/INFO/WARNING/ERROR)
        log_file:     Optional file path for rotating file handler
        json_format:  If True, emit JSON log lines (for log aggregation)
        service_name: Added to JSON log records as "service" field
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    if json_format:
        fmt = _JSONFormatter(service_name=service_name)
    else:
        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        handlers.append(fh)

    for handler in handlers:
        handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("grpc", "asyncio", "websockets", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class _JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def __init__(self, service_name: str = "brain_ai") -> None:
        super().__init__()
        self._service = service_name

    def format(self, record: logging.LogRecord) -> str:
        import json
        payload = {
            "ts":      self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":   record.levelname,
            "service": self._service,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
