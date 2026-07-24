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
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from utils.logger import get_logger

logger = get_logger(__name__)


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


class RedGiantImageScraper(ImageScraper):
    """Sources candidate images live from redgiant.co.ke.

    Strategy, cheapest-first:
      1. Hit the site's WordPress search endpoint (`/?s=<query>`) and
         pull every `<img>` on the results page - this biases toward
         images that are actually relevant to the event/query.
      2. If that page has no usable images (search returned nothing,
         or the theme lazy-loads everything with no dimensions), fall
         back to scraping the homepage so a page is never left with
         zero candidates just because the search query was too
         specific.

    This only ever reads HTML (via `requests` + `BeautifulSoup`) - it
    never downloads the images themselves, so it stays fast and never
    writes third-party binaries to disk. `ImageService` receives the
    `source_url` and templates/the HTML builder simply reference it
    directly (or a later step can download it - see README for the
    `IMAGE_SOURCE=redgiant` note).

    Network failures (timeouts, DNS, 4xx/5xx) are caught and logged,
    never raised - a scraper failing must degrade to the
    `ImageService` placeholder, not crash the whole page pipeline.
    """

    DEFAULT_BASE_URL = "https://redgiant.co.ke"
    DEFAULT_USER_AGENT = "EventPlatformBot/1.0 (+https://redgiant.co.ke; image sourcing pilot)"

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 10.0,
        session: "requests.Session | None" = None,
        user_agent: str | None = None,
    ) -> None:
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", user_agent or self.DEFAULT_USER_AGENT)

    def search(self, query: str, *, limit: int = 5) -> List[ImageCandidate]:
        try:
            candidates = self._search_via_site_search(query, limit)
            if candidates:
                return candidates
            logger.info("RedGiantImageScraper: no images from search for %r, falling back to homepage.", query)
            return self._scrape(self._base_url, limit)
        except requests.RequestException as exc:
            logger.warning("RedGiantImageScraper: request failed for query %r: %s", query, exc)
            return []

    def _search_via_site_search(self, query: str, limit: int) -> List[ImageCandidate]:
        url = f"{self._base_url}/?s={quote_plus(query)}"
        return self._scrape(url, limit)

    def _scrape(self, url: str, limit: int) -> List[ImageCandidate]:
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        return self._extract_images(response.text, limit)

    def _extract_images(self, html: str, limit: int) -> List[ImageCandidate]:
        soup = BeautifulSoup(html, "html.parser")
        candidates: List[ImageCandidate] = []
        seen: set[str] = set()

        for img in soup.find_all("img"):
            # Prefer lazy-load attributes (common on WordPress themes)
            # over `src`, which is often a tiny placeholder.
            raw_src = (
                img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("src")
            )
            if not raw_src or raw_src.startswith("data:"):
                continue

            absolute_url = urljoin(self._base_url + "/", raw_src)
            if absolute_url in seen:
                continue
            seen.add(absolute_url)

            candidates.append(
                ImageCandidate(
                    url=absolute_url,
                    width=_parse_int(img.get("width")),
                    height=_parse_int(img.get("height")),
                    source="redgiant.co.ke",
                )
            )
            if len(candidates) >= limit:
                break

        return candidates


def _parse_int(value: object) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
