"""
providers/mock_provider.py
---------------------------
Deterministic, offline implementation of AIProvider.

Used as the default provider (AI_PROVIDER=mock) so the whole
pipeline - including CI and unit tests - can run without network
access or an API key. It produces plausible, readable placeholder
copy rather than lorem-ipsum, so generated pages are useful for
reviewing layout/SEO structure before switching to a live model.
"""

from __future__ import annotations

from providers.ai_provider import AIProvider, AIResponse, AIUsage


class MockProvider(AIProvider):
    """Rule-based text generator with no external dependencies."""

    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int = 1024) -> AIResponse:
        text = self._synthesize(prompt)
        # Token counts are estimated (roughly 1 token per 4 characters,
        # a common English-text heuristic) rather than measured, since
        # there is no real model tokenizer involved. This keeps the
        # token-usage logging pipeline exercised end-to-end even when
        # running fully offline.
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(text) // 4)
        return AIResponse(text=text, usage=AIUsage(input_tokens=input_tokens, output_tokens=output_tokens))

    @staticmethod
    def _synthesize(prompt: str) -> str:
        """Turn a prompt into short, readable filler copy.

        Prompts built by ContentService end with a dedicated
        ``Topic: <event name> - <section>`` line specifically so this
        heuristic has something short and clean to key off, instead
        of echoing the full instructional prompt back into the page.
        """
        topic_line = next(
            (line for line in reversed(prompt.strip().splitlines()) if line.strip().startswith("Topic:")),
            None,
        )
        topic = topic_line.split("Topic:", 1)[1].strip() if topic_line else "This event"
        return (
            f"{topic}. Attendees can expect a well-organized experience with clear "
            f"logistics, engaging content, and opportunities to connect with other "
            f"participants. Full details, including schedule and access information, "
            f"are provided below."
        )
