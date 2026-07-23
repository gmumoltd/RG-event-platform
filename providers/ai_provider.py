"""
providers/ai_provider.py
-------------------------
Abstract interface every AI backend must implement.

Services (ContentService, ImageService) depend on this interface,
never on a concrete provider. That is the Dependency Inversion half
of SOLID in action: high-level policy (what content to generate)
doesn't depend on low-level detail (which vendor's API produced it).

Adding a new provider (e.g. OpenAI, a local model) means writing one
new class here and registering it in `config/settings.get_ai_provider`
- see ARCHITECTURE.md, "How to add a new AI provider".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class AIUsage:
    """Token accounting for a single generation call."""

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class AIResponse:
    """Result of a single AIProvider.generate() call."""

    text: str
    usage: AIUsage


class AIProvider(ABC):
    """Contract for anything that can turn a prompt into text."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Generate text for `prompt` and report token usage.

        Implementations must be side-effect free with respect to the
        rest of the system (no writing to Context, no file I/O) so
        they can be swapped or mocked freely in tests.
        """
        raise NotImplementedError
