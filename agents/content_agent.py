"""
agents/content_agent.py
--------------------------
Reads Event from Context, calls ContentService, stores the resulting
GeneratedContent back on Context. No SEO/copywriting logic lives
here - that belongs to ContentService, which this agent depends on
only through its public interface.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.context import Context
from services.content_service import ContentService


class ContentAgent(BaseAgent):
    name = "ContentAgent"

    def __init__(self, content_service: ContentService) -> None:
        super().__init__()
        self._content_service = content_service

    def run(self, context: Context) -> Context:
        content, usage = self._content_service.generate(context.event)
        context.content = content
        self._last_usage = usage
        return context
