"""
Unit tests demonstrating the architecture's testability: services can
be tested in complete isolation, with in-memory fakes instead of
real files, network calls, or a running orchestrator.
"""

from __future__ import annotations

from models.event import Event
from providers.mock_provider import MockProvider
from services.content_service import ContentService

RULES = {
    "default": {
        "template": "base.html",
        "seo": {
            "title_pattern": "{event_name} | Guide",
            "meta_description": "About {event_name}.",
            "slug_pattern": "{event_slug}",
        },
        "content": {"sections": ["Overview"]},
        "images": {"alt_pattern": "Photo of {event_name}"},
    }
}


def test_content_service_generates_expected_fields():
    event = Event.from_dict({"name": "Test Event", "subtype": "unknown-subtype"})
    service = ContentService(MockProvider(), RULES)

    content, usage = service.generate(event)

    assert content.title_tag == "Test Event | Guide"
    assert content.meta_description == "About Test Event."
    assert content.slug == "test-event"
    assert content.h1 == "Test Event"
    assert len(content.sections) == 1
    assert content.sections[0].heading == "Overview"
    assert usage.total_tokens > 0


def test_event_from_dict_requires_name():
    import pytest

    with pytest.raises(ValueError):
        Event.from_dict({"subtype": "concert"})
