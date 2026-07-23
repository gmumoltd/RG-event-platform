from __future__ import annotations

from models.event import Event
from services.linking_service import LinkingService

RULES = {
    "default": {"seo": {"slug_pattern": "{event_slug}"}, "linking": {"max_related": 2}},
    "concert": {"seo": {"slug_pattern": "concerts/{event_slug}"}, "linking": {"max_related": 2}},
}


def test_related_links_exclude_self_and_other_subtypes():
    a = Event.from_dict({"name": "A", "subtype": "concert"})
    b = Event.from_dict({"name": "B", "subtype": "concert"})
    c = Event.from_dict({"name": "C", "subtype": "webinar"})

    service = LinkingService(base_url="https://example.com", rules=RULES)
    links = service.build_links(a, [a, b, c])

    labels = [link.label for link in links.related_links]
    assert "B" in labels
    assert "A" not in labels
    assert "C" not in labels
    assert links.breadcrumbs[0].label == "Home"
    assert links.breadcrumbs[-1].label == "A"
