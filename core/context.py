"""
core/context.py
----------------
The shared blackboard that every agent reads from and writes to.

Design rule (enforced by convention + code review, not by the type
system): agents NEVER call each other directly. An agent only ever
receives a `Context`, reads what it needs from it, and writes its own
result back onto it. This is what lets the Orchestrator reorder,
add, or remove agents without any agent needing to know the others
exist.

Attribute access (`context.event`, `context.content`, ...) is used
instead of a raw dict so that typos surface as `AttributeError` at
the point of the mistake instead of silently returning `None` from a
`dict.get`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, List, Optional

from models.content import GeneratedContent
from models.event import Event
from models.image import ImageData
from models.link import LinkData


@dataclass
class AgentRunRecord:
    """Bookkeeping for one agent's execution, used for logging/metrics."""

    agent_name: str
    duration_seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None


@dataclass
class Context:
    """Shared, mutable state passed through the agent pipeline for one event."""

    event: Event
    content: Optional[GeneratedContent] = None
    images: Optional[ImageData] = None
    links: Optional[LinkData] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Observability - not business data, but useful to carry alongside it
    # so the orchestrator/logger can report on a run without a second
    # side-channel object.
    run_history: List[AgentRunRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def record_run(self, record: AgentRunRecord) -> None:
        self.run_history.append(record)
        if record.error:
            self.errors.append(f"{record.agent_name}: {record.error}")

    @property
    def total_tokens(self) -> int:
        return sum(r.input_tokens + r.output_tokens for r in self.run_history)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class StepTimer:
    """Small context manager used by agents/orchestrator to time a step.

    Usage:
        with StepTimer() as timer:
            ...
        elapsed = timer.elapsed
    """

    def __enter__(self) -> "StepTimer":
        self._start = perf_counter()
        self.elapsed = 0.0
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = perf_counter() - self._start
