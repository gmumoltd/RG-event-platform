"""
agents/base_agent.py
----------------------
Abstract base every pipeline agent implements.

Two methods matter:

- `run(context)` - the ONLY method subclasses implement. Pure
  business wiring: read what you need from `context`, call your
  service, write the result back onto `context`, return it.

- `execute(context)` - called by the Orchestrator. A template method
  that wraps `run()` with timing and error handling, so no individual
  agent has to duplicate try/except/logging boilerplate. Errors are
  caught here (not re-raised) so one failing agent doesn't crash the
  whole pipeline for every remaining event/agent - it's recorded on
  the Context and surfaced by the Orchestrator/logger instead.

Agents that call an AIProvider can report token usage by setting
`self._last_usage` during `run()`; `execute()` picks it up afterwards.
This keeps the `run(context) -> Context` contract identical for every
agent, whether or not it happens to consume AI tokens.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.context import AgentRunRecord, Context, StepTimer
from providers.ai_provider import AIUsage
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Contract: every agent reads/writes only via the shared Context."""

    name: str = "BaseAgent"

    def __init__(self) -> None:
        self._last_usage: Optional[AIUsage] = None

    @abstractmethod
    def run(self, context: Context) -> Context:
        """Perform this agent's single responsibility and return the (mutated) context."""
        raise NotImplementedError

    def execute(self, context: Context) -> Context:
        """Timed, error-safe wrapper around `run()`. Called by the Orchestrator."""
        self._last_usage = None
        error_message: Optional[str] = None

        with StepTimer() as timer:
            try:
                context = self.run(context)
            except Exception as exc:  # noqa: BLE001 - isolate failures per agent
                error_message = str(exc)
                logger.error("Agent '%s' failed for event '%s': %s", self.name, context.event.name, exc)

        usage = self._last_usage or AIUsage(input_tokens=0, output_tokens=0)
        context.record_run(
            AgentRunRecord(
                agent_name=self.name,
                duration_seconds=timer.elapsed,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                error=error_message,
            )
        )
        return context
