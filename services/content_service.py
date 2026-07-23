"""
services/content_service.py
------------------------------
Business logic for turning an `Event` into `GeneratedContent`.

This is where the original prototype's `ContentSEOAgent.generate()`
logic now lives, reworked to:
  - operate on the typed `Event` model instead of a raw dict
  - read rules from an injected dict rather than a module-level path
  - delegate section copywriting to an injected `AIProvider`
  - return a typed `GeneratedContent` plus token-usage information

`ContentAgent` (agents/content_agent.py) is a thin wrapper that calls
this service and stores the result on the shared `Context`. All the
actual decision-making - which rules apply, how sections are
assembled, how the AI is prompted - lives here, where it can be unit
tested without any agent/orchestrator machinery.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from config.constants import FALLBACK_RULE_KEY
from models.content import ContentSection, GeneratedContent
from models.event import Event
from providers.ai_provider import AIProvider, AIUsage


class ContentService:
    def __init__(self, ai_provider: AIProvider, rules: Dict[str, Any]) -> None:
        self._ai_provider = ai_provider
        self._rules = rules

    def generate(self, event: Event) -> Tuple[GeneratedContent, AIUsage]:
        """Generate SEO content for `event`, returning it with aggregate token usage."""
        subtype_rules = self._rules_for(event.subtype)
        seo_rules = subtype_rules.get("seo", {})

        title_tag = self._safe_format(seo_rules.get("title_pattern", "{event_name}"), event)
        meta_description = self._safe_format(
            seo_rules.get("meta_description", "Learn more about {event_name}."), event
        )
        slug = self._safe_format(seo_rules.get("slug_pattern", "{event_slug}"), event)

        section_names = subtype_rules.get("content", {}).get("sections", ["Overview"])
        sections = []
        total_input = 0
        total_output = 0

        for section_name in section_names:
            prompt = self._build_section_prompt(event, section_name)
            response = self._ai_provider.generate(prompt, max_tokens=250)
            sections.append(ContentSection(heading=section_name, html=f"<p>{response.text}</p>"))
            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

        content = GeneratedContent(
            title_tag=title_tag,
            meta_description=meta_description,
            slug=slug,
            h1=event.name,
            sections=sections,
        )
        return content, AIUsage(input_tokens=total_input, output_tokens=total_output)

    # -- internal helpers ----------------------------------------------------

    def _rules_for(self, subtype: str) -> Dict[str, Any]:
        return self._rules.get(subtype) or self._rules.get(FALLBACK_RULE_KEY, {})

    @staticmethod
    def _safe_format(pattern: str, event: Event) -> str:
        return pattern.format(event_name=event.name, event_slug=event.slug_base, category=event.category)

    @staticmethod
    def _build_section_prompt(event: Event, section_name: str) -> str:
        details = ", ".join(
            filter(
                None,
                [
                    f"location: {event.location}" if event.location else None,
                    f"date: {event.date}" if event.date else None,
                    f"organizer: {event.organizer}" if event.organizer else None,
                    event.description,
                ],
            )
        )
        return (
            f"Write one concise, factual paragraph (2-3 sentences) for the "
            f"'{section_name}' section of an SEO landing page about the event "
            f"'{event.name}'. Known details: {details or 'none provided'}. "
            f"Do not invent specific facts (times, prices, names) that were not given.\n"
            f"Topic: {event.name} - {section_name}"
        )
