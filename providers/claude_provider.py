"""
providers/claude_provider.py
------------------------------
Live implementation of AIProvider backed by the Anthropic Claude API.

Requires the `anthropic` package (see requirements.txt) and an API
key, supplied via the CLAUDE_API_KEY (or ANTHROPIC_API_KEY)
environment variable - see config/settings.py.

This class intentionally does nothing except talk to the API and
translate the response into our own `AIResponse`/`AIUsage` types. It
has no knowledge of events, rules, or HTML - that separation is what
lets ContentService and ImageService stay provider-agnostic.
"""

from __future__ import annotations

from typing import Optional

from providers.ai_provider import AIProvider, AIResponse, AIUsage


class ClaudeProviderError(RuntimeError):
    """Raised when the Claude API call fails or returns an unusable response."""


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str, model: str, default_max_tokens: int = 1024) -> None:
        if not api_key:
            raise ValueError("ClaudeProvider requires a non-empty api_key.")

        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the dep installed
            raise ClaudeProviderError(
                "The 'anthropic' package is required to use ClaudeProvider. "
                "Install it with: pip install anthropic"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._default_max_tokens = default_max_tokens

    def generate(self, prompt: str, *, system: Optional[str] = None, max_tokens: int = None) -> AIResponse:  # type: ignore[assignment]
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or self._default_max_tokens,
                system=system or "You are an expert SEO copywriter for an event listings platform.",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/network failure uniformly
            raise ClaudeProviderError(f"Claude API request failed: {exc}") from exc

        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        usage = AIUsage(
            input_tokens=getattr(response.usage, "input_tokens", 0),
            output_tokens=getattr(response.usage, "output_tokens", 0),
        )
        return AIResponse(text=text.strip(), usage=usage)
