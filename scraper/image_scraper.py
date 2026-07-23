"""
scraper/image_scraper.py
--------------------------
Image-sourcing architecture, kept deliberately independent of
`agents/image_agent.py` and `services/image_service.py`.

Why a separate layer instead of scraping directly inside ImageAgent?
- Swapping the source (a stock-photo API, a self-hosted image
  library, a web scraper) never touches agent or service code.
- Scrapers are I/O-heavy and slow; isolating them behind a narrow
  interface makes them trivial to mock in tests (see
  `NullImageScraper` below, used by default).

`ImageService` (services/image_service.py) depends on the
`ImageScraper` interface only, never on a concrete scraper.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True, slots=True)
class ImageCandidate:
    """One candidate image returned by a scraper, before final selection."""

    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    source: Optional[str] = None
    license: Optional[str] = None


class ImageScraper(ABC):
    """Contract for anything that can find candidate images for a query."""

    @abstractmethod
    def search(self, query: str, *, limit: int = 5) -> List[ImageCandidate]:
        raise NotImplementedError


class NullImageScraper(ImageScraper):
    """Default, network-free scraper.

    Returns no candidates, which causes `ImageService` to fall back to
    a locally generated placeholder image reference. This keeps
    `python main.py` runnable in any environment (including CI and
    sandboxes with no network egress) without special-casing.

    Swap this for a real implementation (e.g. an Unsplash/Pexels API
    client, or an internal DAM search) by registering it in
    `services/image_service.py` construction - see ARCHITECTURE.md.
    """

    def search(self, query: str, *, limit: int = 5) -> List[ImageCandidate]:
        return []


class StaticImageScraper(ImageScraper):
    """Looks up candidates from an in-memory mapping.

    Useful for tests and for demos/offline environments where a fixed
    set of known-good image URLs should be used instead of a live
    web search.
    """

    def __init__(self, catalogue: dict[str, List[ImageCandidate]] | None = None) -> None:
        self._catalogue = catalogue or {}

    def search(self, query: str, *, limit: int = 5) -> List[ImageCandidate]:
        key = query.strip().lower()
        return self._catalogue.get(key, [])[:limit]
