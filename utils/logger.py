"""
utils/logger.py
-----------------
Structured logging for the platform.

Two things live here:

1. `get_logger(name)` - a standard `logging.Logger`, configured once,
   that every module uses instead of `print()`. Supports plain-text
   (readable in a terminal) or JSON output (LOG_JSON=true), so the
   same code produces log lines a log-aggregation service can parse.

2. `TokenUsageLogger` - a narrow CSV writer for AI token accounting
   (per the brief's "Log ... AI token usage" requirement), kept
   separate from the general logger because it's structured, queryable
   data (for a cost dashboard/spreadsheet), not a human-readable log
   stream.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from config.constants import APP_LOG_PATH, LOGS_DIR, TOKEN_USAGE_LOG_PATH

_CONFIGURED = False
_CONFIG_LOCK = Lock()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _configure_root(log_level: str = "INFO", json_output: bool = False) -> None:
    global _CONFIGURED
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger("event_platform")
        root.setLevel(log_level)
        root.propagate = False

        formatter: logging.Formatter
        if json_output:
            formatter = _JsonFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

        file_handler = logging.FileHandler(APP_LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        _CONFIGURED = True


def get_logger(name: str, *, log_level: Optional[str] = None, json_output: Optional[bool] = None) -> logging.Logger:
    """Return a configured logger for `name`, configuring the root handler set on first use."""
    if not _CONFIGURED:
        try:
            from config.settings import get_settings

            settings = get_settings()
            _configure_root(log_level or settings.log_level, json_output if json_output is not None else settings.log_json)
        except Exception:
            # Settings may not be importable in some minimal contexts
            # (e.g. very early bootstrap); fall back to sane defaults
            # rather than let logging setup break the whole app.
            _configure_root(log_level or "INFO", bool(json_output))

    return logging.getLogger(f"event_platform.{name}")


class TokenUsageLogger:
    """Appends one CSV row per agent execution: who used how many tokens, on what."""

    _FIELDNAMES = ["timestamp", "event_name", "agent_name", "input_tokens", "output_tokens", "total_tokens"]

    def __init__(self, path: Path = TOKEN_USAGE_LOG_PATH) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            with self._path.open("w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=self._FIELDNAMES).writeheader()

    def log(self, event_name: str, agent_name: str, input_tokens: int, output_tokens: int) -> None:
        with self._path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._FIELDNAMES)
            writer.writerow(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_name": event_name,
                    "agent_name": agent_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                }
            )

    def log_context(self, context) -> None:
        """Convenience: log every AgentRunRecord already collected on a Context."""
        for record in context.run_history:
            self.log(context.event.name, record.agent_name, record.input_tokens, record.output_tokens)
