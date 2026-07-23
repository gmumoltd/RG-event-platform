"""
seo/schema.py
---------------
Builds schema.org JSON-LD structured data for an event page.

Returns a plain dict (not a pre-serialized string) so the HTML
builder controls exactly how/where it's embedded, and so tests can
assert on structure without string-matching JSON text.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from config.constants import SCHEMA_CONTEXT, SCHEMA_EVENT_TYPE
from core.context import Context


def build_event_schema(context: Context, base_url: str) -> Dict[str, Any]:
    event = context.event
    schema: Dict[str, Any] = {
        "@context": SCHEMA_CONTEXT,
        "@type": SCHEMA_EVENT_TYPE,
        "name": event.name,
    }

    if event.date:
        schema["startDate"] = event.date
    if event.location:
        schema["location"] = {"@type": "Place", "name": event.location}
    if event.organizer:
        schema["organizer"] = {"@type": "Organization", "name": event.organizer}
    if event.description:
        schema["description"] = event.description
    if context.images:
        schema["image"] = f"{base_url.rstrip('/')}/images/{context.images.filename}"
    if context.content:
        schema["url"] = f"{base_url.rstrip('/')}/{context.content.slug}.html"

    return schema


def build_event_schema_json(context: Context, base_url: str) -> str:
    return json.dumps(build_event_schema(context, base_url), indent=2)
