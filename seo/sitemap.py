"""
seo/sitemap.py
-----------------
Site-level SEO artifacts that aren't tied to a single event page:
`sitemap.xml` (one <url> entry per generated page) and `robots.txt`.

These operate over a list of Contexts (one full pipeline run's worth
of results), not a single Context, which is why they live apart from
`seo/metadata.py` and `seo/schema.py`.
"""

from __future__ import annotations

from typing import Iterable
from xml.sax.saxutils import escape

from core.context import Context


def build_sitemap_xml(contexts: Iterable[Context], base_url: str) -> str:
    base_url = base_url.rstrip("/")
    urls = []
    for context in contexts:
        if not context.content:
            continue
        loc = f"{base_url}/{context.content.slug}.html"
        urls.append(f"  <url>\n    <loc>{escape(loc)}</loc>\n  </url>")

    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def build_robots_txt(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    return "User-agent: *\nAllow: /\n\n" f"Sitemap: {base_url}/sitemap.xml\n"
