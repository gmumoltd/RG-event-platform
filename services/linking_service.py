"""
services/linking_service.py
------------------------------
Business logic for building an event page's internal-linking graph:
related events, breadcrumbs, and internal navigation links.

Mirrors the original `InterlinkingAgent.build_links()` prototype
logic (same-subtype related events) but returns typed `LinkData`
instead of a raw HTML string, and separates link *data* from link
*markup* - rendering `<a>` tags is the HTML builder's job
(assembler/html_builder.py), not this service's.
"""

from __future__ import annotations

from typing import Any, Dict, List

from config.constants import FALLBACK_RULE_KEY
from models.event import Event
from models.link import LinkData, LinkItem


class LinkingService:
    def __init__(self, base_url: str, rules: Dict[str, Any]) -> None:
        self._base_url = base_url.rstrip("/")
        self._rules = rules

    def build_links(self, event: Event, all_events: List[Event]) -> LinkData:
        subtype_rules = self._rules_for(event.subtype)
        max_related = subtype_rules.get("linking", {}).get("max_related", 4)

        related = [
            e for e in all_events if e.subtype == event.subtype and e.name != event.name
        ][:max_related]
        related_links = [LinkItem(label=e.name, url=self._page_url(e)) for e in related]

        breadcrumbs = [
            LinkItem(label="Home", url=f"{self._base_url}/"),
            LinkItem(label=event.category.title(), url=f"{self._base_url}/{event.category}/"),
            LinkItem(label=event.subtype.title(), url=f"{self._base_url}/{event.subtype}/"),
            LinkItem(label=event.name, url=self._page_url(event)),
        ]

        internal_links = [
            LinkItem(label=f"All {event.subtype} events", url=f"{self._base_url}/{event.subtype}/"),
            LinkItem(label="Browse all events", url=f"{self._base_url}/"),
        ]

        return LinkData(related_links=related_links, breadcrumbs=breadcrumbs, internal_links=internal_links)

    # -- internal helpers ----------------------------------------------------

    def _rules_for(self, subtype: str) -> Dict[str, Any]:
        return self._rules.get(subtype) or self._rules.get(FALLBACK_RULE_KEY, {})

    def _page_url(self, event: Event) -> str:
        slug_pattern = self._rules_for(event.subtype).get("seo", {}).get("slug_pattern", "{event_slug}")
        slug = slug_pattern.format(event_name=event.name, event_slug=event.slug_base, category=event.category)
        return f"{self._base_url}/{slug}.html"
