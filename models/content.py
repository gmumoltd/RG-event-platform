"""
models/content.py
------------------
Output of the content-generation pipeline (ContentService /
ContentAgent). Deliberately separate from `Event` (the input) so the
two can evolve independently - e.g. adding a new SEO field here never
requires touching the source-data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True, slots=True)
class ContentSection:
    """One rendered section of the page body (e.g. "Agenda", "Speakers")."""

    heading: str
    html: str


@dataclass(frozen=True, slots=True)
class GeneratedContent:
    """SEO-optimized copy generated for a single event."""

    title_tag: str
    meta_description: str
    slug: str
    h1: str
    sections: List[ContentSection] = field(default_factory=list)

    @property
    def body_html(self) -> str:
        """Concatenated HTML for all sections, ready to drop into a template."""
        return "\n".join(f"<h2>{s.heading}</h2>\n{s.html}" for s in self.sections)
