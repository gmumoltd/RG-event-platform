"""
agents/orchestrator.py
-------------------------
Executes a registered, ordered sequence of agents over a single
shared Context. Knows nothing about content, images, or links - only
how to run "the next agent" and hand it the same Context.

Adding a new agent to the pipeline requires exactly one line at the
call site (`registry.register("faq", FaqAgent(...))`) - see
ARCHITECTURE.md, "How to add a new agent". The Orchestrator's code
never changes.
"""

from __future__ import annotations

from core.context import Context
from core.registry import AgentRegistry
from utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """Runs every registered agent, in registration order, over a Context."""

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self._registry = registry or AgentRegistry()

    def register(self, name: str, agent) -> "Orchestrator":
        self._registry.register(name, agent)
        return self

    def run(self, context: Context) -> Context:
        logger.info("Starting pipeline for event '%s' (%d agents)", context.event.name, len(self._registry))

        for name, agent in self._registry:
            context = agent.execute(context)

        if context.has_errors:
            logger.warning(
                "Pipeline for '%s' completed with %d error(s): %s",
                context.event.name,
                len(context.errors),
                "; ".join(context.errors),
            )
        else:
            logger.info(
                "Pipeline for '%s' completed successfully (%d tokens used)",
                context.event.name,
                context.total_tokens,
            )

        return context
