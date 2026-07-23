"""
assembler/html_builder.py
----------------------------
Consumes a Context (after the full agent pipeline has run) and
produces the final SEO-ready HTML page, plus the site-level listing
page. All templating logic (Jinja2) is isolated here - agents and
services never import Jinja2 or know templates exist.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.constants import FALLBACK_RULE_KEY, FALLBACK_TEMPLATE, TEMPLATES_DIR
from core.context import Context
from seo import metadata, schema


class HTMLBuilder:
    def __init__(self, base_url: str, site_name: str, twitter_handle: str, rules: Dict[str, Any]) -> None:
        self._base_url = base_url
        self._site_name = site_name
        self._twitter_handle = twitter_handle
        self._rules = rules
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(enabled_extensions=("html",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_page(self, context: Context) -> str:
        """Render the full SEO-ready HTML page for one event's Context."""
        template_name = self._template_for(context.event.subtype)
        template = self._env.get_template(template_name)

        return template.render(
            event=context.event,
            content=context.content,
            images=context.images,
            links=context.links,
            meta=metadata.build_meta_tags(context),
            og=metadata.build_open_graph_tags(context, self._base_url, self._site_name),
            twitter=metadata.build_twitter_card_tags(context, self._twitter_handle),
            schema_json=schema.build_event_schema_json(context, self._base_url),
            canonical_url=metadata.build_canonical_url(context, self._base_url),
            site_name=self._site_name,
        )

    def build_listing_page(self, contexts: Iterable[Context]) -> str:
        """Render the site-wide index page linking to every generated event page."""
        template = self._env.get_template("listing.html")

        events_by_subtype: Dict[str, List[Dict[str, str]]] = {}
        for context in contexts:
            if not context.content:
                continue
            events_by_subtype.setdefault(context.event.subtype, []).append(
                {"name": context.event.name, "url": f"{context.content.slug}.html"}
            )

        return template.render(
            site_name=self._site_name,
            base_url=self._base_url,
            events_by_subtype=events_by_subtype,
        )

    def _template_for(self, subtype: str) -> str:
        subtype_rules = self._rules.get(subtype) or self._rules.get(FALLBACK_RULE_KEY, {})
        return subtype_rules.get("template", FALLBACK_TEMPLATE)
