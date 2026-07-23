"""
utils/file_manager.py
------------------------
All filesystem I/O funnels through here: reading JSON/YAML input
files and writing generated output files. Keeping I/O in one small
module means:

- services/agents never touch `open()` directly, so they stay
  trivially unit-testable (no tmp files needed).
- Path handling (creating output dirs, encoding) is defined once.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
