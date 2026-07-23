"""
models/image.py
----------------
Output of the image pipeline (ImageService / ImageAgent / scraper).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class ImageData:
    """The hero image selected for an event's landing page."""

    filename: str
    alt_text: str
    source_url: Optional[str] = None
    caption: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    license: Optional[str] = None
