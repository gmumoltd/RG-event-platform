"""
seo/metadata.py
-----------------
Pure functions that turn a Context into the various head-tag
structures a template needs: standard meta tags, Open Graph, Twitter
Cards, and the canonical URL.

Pure/stateless by design (no Context mutation, no I/O) so the HTML
builder - or a future JSON API - can call these without any hidden
coupling.
"""

from __future__ import annotations

from typing import Dict

from config.constants import DEFAULT_LOCALE, DEFAULT_TWITTER_CARD_TYPE
from core.context import Context


def build_canonical_url(context: Context, base_url: str) -> str:
    slug = context.content.slug if context.content else context.event.slug_base
    return f"{base_url.rstrip('/')}/{slug}.html"


def build_meta_tags(context: Context) -> Dict[str, str]:
    content = context.content
    return {
        "title": content.title_tag if content else context.event.name,
        "description": content.meta_description if content else "",
        "robots": "index, follow",
        "locale": DEFAULT_LOCALE,
    }


def build_open_graph_tags(context: Context, base_url: str, site_name: str) -> Dict[str, str]:
    content = context.content
    canonical = build_canonical_url(context, base_url)
    tags = {
        "og:type": "website",
        "og:site_name": site_name,
        "og:title": content.title_tag if content else context.event.name,
        "og:description": content.meta_description if content else "",
        "og:url": canonical,
    }
    if context.images:
        tags["og:image"] = f"{base_url.rstrip('/')}/images/{context.images.filename}"
        tags["og:image:alt"] = context.images.alt_text
    return tags


def build_twitter_card_tags(context: Context, twitter_handle: str) -> Dict[str, str]:
    content = context.content
    tags = {
        "twitter:card": DEFAULT_TWITTER_CARD_TYPE,
        "twitter:site": twitter_handle,
        "twitter:title": content.title_tag if content else context.event.name,
        "twitter:description": content.meta_description if content else "",
    }
    if context.images:
        tags["twitter:image"] = context.images.filename
    return tags
