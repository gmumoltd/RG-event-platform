"""
agents/image_agent.py
------------------------
Reads Event (and, where relevant, the already-generated content) from
Context, determines hero image requirements via ImageService, and
stores the resulting ImageData back on Context.

Runs after ContentAgent in the default pipeline (see main.py) so that,
if a future ImageService wants to factor in the generated copy (e.g.
picking imagery that matches a specific section), that data is
already available on the Context - without ImageAgent ever calling
ContentAgent directly.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.context import Context
from services.image_service import ImageService


class ImageAgent(BaseAgent):
    name = "ImageAgent"

    def __init__(self, image_service: ImageService) -> None:
        super().__init__()
        self._image_service = image_service

    def run(self, context: Context) -> Context:
        context.images = self._image_service.source_image(context.event)
        return context
