"""
core/registry.py
-----------------
A minimal ordered registry of (name -> agent) pairs.

Pulled out of `Orchestrator` itself so that "how agents are stored
and ordered" is a separate concern from "how agents are executed".
This is what makes adding a new agent a pure registration call - see
ARCHITECTURE.md, "How to add a new agent".
"""

from __future__ import annotations

from typing import Iterator, List, Tuple

from agents.base_agent import BaseAgent


class AgentRegistry:
    """Ordered collection of named agents.

    Order of registration = order of execution. Duplicate names are
    rejected so a copy/paste mistake in `main.py` fails loudly at
    startup instead of silently double-registering an agent.
    """

    def __init__(self) -> None:
        self._agents: List[Tuple[str, BaseAgent]] = []
        self._names: set[str] = set()

    def register(self, name: str, agent: BaseAgent) -> "AgentRegistry":
        if name in self._names:
            raise ValueError(f"An agent named '{name}' is already registered.")
        self._agents.append((name, agent))
        self._names.add(name)
        return self  # allow fluent chaining: registry.register(...).register(...)

    def __iter__(self) -> Iterator[Tuple[str, BaseAgent]]:
        return iter(self._agents)

    def __len__(self) -> int:
        return len(self._agents)

    def names(self) -> List[str]:
        return [name for name, _ in self._agents]
