"""
core/pipeline.py
-------------------
`PipelineRunner` ties the whole system together for one end-to-end
run: load data, build a Context per event, run the agent pipeline for
each, then produce the site-level artifacts (listing page, sitemap,
robots.txt) once all events are processed.

This is the "business logic" that the brief says must NOT live in
`main.py`. `main.py` only constructs a `PipelineRunner` (dependency
injection) and calls `.run_all()` - see main.py for the composition
root.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.content_agent import ContentAgent
from agents.image_agent import ImageAgent
from agents.linking_agent import LinkingAgent
from agents.orchestrator import Orchestrator
from config.constants import EVENTS_PATH, OUTPUT_DIR, RULES_PATH
from config.settings import Settings
from core.context import Context
from core.registry import AgentRegistry
from models.event import Event
from providers.ai_provider import AIProvider
from scraper.image_scraper import ImageScraper, NullImageScraper
from scraper.selector import ImageSelector
from services.content_service import ContentService
from services.image_service import ImageService
from services.linking_service import LinkingService
from utils.file_manager import read_json, read_yaml, write_text
from utils.logger import TokenUsageLogger, get_logger
from utils.validator import validate_rules, validate_raw_events

logger = get_logger(__name__)


class PipelineRunner:
    """Composition of services + agents + orchestrator for a full site build."""

    def __init__(
        self,
        settings: Settings,
        ai_provider: AIProvider,
        image_scraper: ImageScraper | None = None,
    ) -> None:
        self._settings = settings
        self._rules: Dict[str, Any] = validate_rules(read_yaml(RULES_PATH))

        self._content_service = ContentService(ai_provider, self._rules)
        self._image_service = ImageService(image_scraper or NullImageScraper(), ImageSelector(), self._rules)
        self._linking_service = LinkingService(settings.base_url, self._rules)

        self._token_logger = TokenUsageLogger()

        # Deferred import avoids a circular import (html_builder ->
        # config.constants only, so this is just for symmetry/clarity).
        from assembler.html_builder import HTMLBuilder

        self._html_builder = HTMLBuilder(
            base_url=settings.base_url,
            site_name=settings.site_name,
            twitter_handle=settings.twitter_handle,
            rules=self._rules,
        )

    def _build_orchestrator(self) -> Orchestrator:
        """Fresh Orchestrator per event so agent-local state never leaks across events."""
        registry = AgentRegistry()
        registry.register("content", ContentAgent(self._content_service))
        registry.register("image", ImageAgent(self._image_service))
        registry.register("linking", LinkingAgent(self._linking_service))
        return Orchestrator(registry)

    def load_events(self) -> List[Event]:
        raw_events = validate_raw_events(read_json(EVENTS_PATH))
        return [Event.from_dict(raw) for raw in raw_events]

    def run_all(self) -> List[Context]:
        events = self.load_events()
        logger.info("Loaded %d event(s) from %s", len(events), EVENTS_PATH)

        contexts: List[Context] = []
        for event in events:
            context = Context(event=event, metadata={"all_events": events})
            orchestrator = self._build_orchestrator()
            context = orchestrator.run(context)
            self._token_logger.log_context(context)

            if context.content:
                page_html = self._html_builder.build_page(context)
                write_text(OUTPUT_DIR / f"{context.content.slug}.html", page_html)
            else:
                logger.error("Skipping HTML output for '%s' - no content was generated.", event.name)

            contexts.append(context)

        self._write_site_artifacts(contexts)
        return contexts

    def _write_site_artifacts(self, contexts: List[Context]) -> None:
        from seo.sitemap import build_robots_txt, build_sitemap_xml

        listing_html = self._html_builder.build_listing_page(contexts)
        write_text(OUTPUT_DIR / "index.html", listing_html)

        write_text(OUTPUT_DIR / "sitemap.xml", build_sitemap_xml(contexts, self._settings.base_url))
        write_text(OUTPUT_DIR / "robots.txt", build_robots_txt(self._settings.base_url))

        succeeded = sum(1 for c in contexts if c.content and not c.has_errors)
        logger.info(
            "Site build complete: %d/%d pages generated successfully -> %s",
            succeeded,
            len(contexts),
            OUTPUT_DIR,
        )
