"""Logging setup.

Development gets human-readable lines; production emits one JSON object per record so
hosted log collectors can index the fields.
"""

import json
import logging
import sys
from typing import Any

from app.core.config import Settings

# Attributes present on every LogRecord — anything else was attached by the caller via
# `logger.info(..., extra={...})` and belongs in the structured output.
_RESERVED_RECORD_KEYS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class DevFormatter(logging.Formatter):
    """Readable lines that still show the structured fields.

    Without this, anything attached via ``extra={...}`` is silently dropped in development
    and only appears in production's JSON — exactly backwards for debugging. A rejected
    auth token logged its reason into the void.
    """

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        extras = {
            key: value for key, value in record.__dict__.items() if key not in _RESERVED_RECORD_KEYS
        }
        if extras:
            # ASCII only: Windows consoles default to a codepage that mangles punctuation
            # like a middot, and a log line you cannot read is worse than a plain one.
            line += " [" + " ".join(f"{key}={value!r}" for key, value in extras.items()) + "]"
        return line


def configure_logging(settings: Settings) -> None:
    """Install a single stdout handler on the root logger.

    Safe to call more than once: existing handlers are replaced rather than stacked, which
    keeps uvicorn's `--reload` from duplicating every line.
    """
    handler = logging.StreamHandler(sys.stdout)
    if settings.is_production:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(DevFormatter("%(asctime)s %(levelname)-8s %(name)s | %(message)s"))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # uvicorn installs its own handlers; let records bubble up to ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
