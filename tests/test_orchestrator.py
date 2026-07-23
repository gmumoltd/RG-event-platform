from __future__ import annotations

from agents.content_agent import ContentAgent
from agents.image_agent import ImageAgent
from agents.linking_agent import LinkingAgent
from agents.orchestrator import Orchestrator
from core.context import Context
from core.registry import AgentRegistry
from models.event import Event
from providers.mock_provider import MockProvider
from scraper.image_scraper import NullImageScraper
from scraper.selector import ImageSelector
from services.content_service import ContentService
from services.image_service import ImageService
from services.linking_service import LinkingService

RULES = {
    "default": {
        "seo": {
            "title_pattern": "{event_name}",
            "meta_description": "{event_name}",
            "slug_pattern": "{event_slug}",
        },
        "content": {"sections": ["Overview"]},
        "images": {"alt_pattern": "{event_name}"},
        "linking": {"max_related": 3},
    }
}


def build_registry() -> AgentRegistry:
    content_service = ContentService(MockProvider(), RULES)
    image_service = ImageService(NullImageScraper(), ImageSelector(), RULES)
    linking_service = LinkingService("https://example.com", RULES)

    registry = AgentRegistry()
    registry.register("content", ContentAgent(content_service))
    registry.register("image", ImageAgent(image_service))
    registry.register("linking", LinkingAgent(linking_service))
    return registry


def build_orchestrator() -> Orchestrator:
    return Orchestrator(build_registry())


def test_full_pipeline_populates_context_without_errors():
    event = Event.from_dict({"name": "Sample Event", "subtype": "unknown"})
    context = Context(event=event, metadata={"all_events": [event]})

    registry = build_registry()
    result = Orchestrator(registry).run(context)

    assert result.content is not None
    assert result.images is not None
    assert result.links is not None
    assert not result.has_errors
    assert result.total_tokens > 0
    assert registry.names() == ["content", "image", "linking"]


def test_duplicate_agent_registration_raises():
    import pytest

    registry = AgentRegistry()
    registry.register("content", ContentAgent(ContentService(MockProvider(), RULES)))
    with pytest.raises(ValueError):
        registry.register("content", ContentAgent(ContentService(MockProvider(), RULES)))
