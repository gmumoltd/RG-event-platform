"""
agents/linking_agent.py
--------------------------
Reads Context (event + the full event catalogue, made available via
`context.metadata["all_events"]`) and stores related links,
breadcrumbs, and internal links as LinkData.

The full event list is read from `context.metadata` rather than
passed directly to this agent's constructor per-event, so that every
agent keeps the same "reads/writes Context only" shape - this agent
never reaches into another agent or into the Orchestrator to get it.
`main.py` is responsible for populating `context.metadata["all_events"]`
once, when each event's Context is built.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.context import Context
from services.linking_service import LinkingService


class LinkingAgent(BaseAgent):
    name = "LinkingAgent"

    def __init__(self, linking_service: LinkingService) -> None:
        super().__init__()
        self._linking_service = linking_service

    def run(self, context: Context) -> Context:
        all_events = context.metadata.get("all_events", [context.event])
        context.links = self._linking_service.build_links(context.event, all_events)
        return context
