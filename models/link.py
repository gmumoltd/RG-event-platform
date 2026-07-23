"""
models/link.py
---------------
Output of the internal-linking pipeline (LinkingService / LinkingAgent).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True, slots=True)
class LinkItem:
    """A single hyperlink: display label + destination URL."""

    label: str
    url: str


@dataclass(frozen=True, slots=True)
class LinkData:
    """All internal-linking artifacts for one event's page."""

    related_links: List[LinkItem] = field(default_factory=list)
    breadcrumbs: List[LinkItem] = field(default_factory=list)
    internal_links: List[LinkItem] = field(default_factory=list)
