"""
services/image_service.py
----------------------------
Business logic for determining and sourcing an event's hero image.

Mirrors the original `ImageSourcingAgent.scrape_and_select()`
prototype logic (rule-driven alt text, derived filename) but:
  - reads rules from an injected dict
  - delegates candidate discovery to an injected `ImageScraper`
  - delegates ranking to an injected `ImageSelector`
  - falls back to a deterministic placeholder when no candidates are
    found (e.g. the default `NullImageScraper`, or a real scraper
    that simply found nothing), so the pipeline never breaks for
    lack of a live image source.
"""

from __future__ import annotations

from typing import Any, Dict

from config.constants import FALLBACK_RULE_KEY
from models.event import Event
from models.image import ImageData
from scraper.image_scraper import ImageScraper
from scraper.selector import ImageSelector


class ImageService:
    def __init__(self, scraper: ImageScraper, selector: ImageSelector, rules: Dict[str, Any]) -> None:
        self._scraper = scraper
        self._selector = selector
        self._rules = rules

    def source_image(self, event: Event) -> ImageData:
        subtype_rules = self._rules_for(event.subtype)
        image_rules = subtype_rules.get("images", {})

        alt_text = image_rules.get("alt_pattern", "Photo of {event_name}").format(event_name=event.name)
        search_query = image_rules.get("search_query_pattern", "{event_name}").format(event_name=event.name)

        candidates = self._scraper.search(search_query, limit=5)
        best = self._selector.select_best(candidates)

        if best is not None:
            return ImageData(
                filename=f"{event.slug_base}.jpg",
                alt_text=alt_text,
                source_url=best.url,
                width=best.width,
                height=best.height,
                license=best.license,
            )

        # No scraper configured (or nothing found) - deterministic
        # placeholder keeps every page visually complete.
        return ImageData(
            filename=f"{event.slug_base}-placeholder.jpg",
            alt_text=alt_text,
            caption=f"Image for {event.name} coming soon.",
        )

    def _rules_for(self, subtype: str) -> Dict[str, Any]:
        return self._rules.get(subtype) or self._rules.get(FALLBACK_RULE_KEY, {})
