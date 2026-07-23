"""
config/settings.py
-------------------
Centralized, environment-driven configuration.

This is the ONLY place in the codebase that reads `os.environ`
directly. Every other module receives configuration through
constructor injection (a `Settings` instance, or values pulled from
one). That keeps the rest of the system testable: tests can build a
`Settings` object by hand instead of mutating environment variables.

Switching AI providers ("mock" <-> "claude") is a one-line change:
set AI_PROVIDER in the environment (or `.env`) file. Nothing else in
the codebase needs to change, because every consumer depends on the
`AIProvider` interface (see providers/ai_provider.py), not on a
concrete implementation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from config import constants

try:
    # python-dotenv is optional at runtime (mock provider needs no
    # secrets), but recommended for local development so a `.env`
    # file can supply CLAUDE_API_KEY without exporting it manually.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is a soft dependency
    pass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    # --- AI provider selection -------------------------------------------------
    ai_provider: str = field(
        default_factory=lambda: os.getenv("AI_PROVIDER", constants.PROVIDER_MOCK).strip().lower()
    )
    claude_api_key: Optional[str] = field(default_factory=lambda: os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-5"))
    claude_max_tokens: int = field(default_factory=lambda: int(os.getenv("CLAUDE_MAX_TOKENS", "1024")))

    # --- Site / SEO --------------------------------------------------------
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "https://example.com").rstrip("/"))
    site_name: str = field(default_factory=lambda: os.getenv("SITE_NAME", "Event Platform"))
    twitter_handle: str = field(default_factory=lambda: os.getenv("TWITTER_HANDLE", "@events"))

    # --- Behaviour flags -----------------------------------------------------
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    log_json: bool = field(default_factory=lambda: _env_bool("LOG_JSON", False))

    def validate(self) -> None:
        """Fail fast on invalid/incomplete configuration.

        Raising here (rather than deep inside a provider mid-pipeline)
        means misconfiguration is caught during startup, before any
        agent runs.
        """
        if self.ai_provider not in constants.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported AI_PROVIDER '{self.ai_provider}'. "
                f"Expected one of: {', '.join(constants.SUPPORTED_PROVIDERS)}"
            )
        if self.ai_provider == constants.PROVIDER_CLAUDE and not self.claude_api_key:
            raise ValueError(
                "AI_PROVIDER is set to 'claude' but no CLAUDE_API_KEY "
                "(or ANTHROPIC_API_KEY) was found in the environment."
            )


def get_settings() -> Settings:
    """Build a fresh Settings snapshot from the current environment.

    A function rather than a module-level singleton so tests can call
    it after monkeypatching `os.environ` and get a clean result.
    """
    return Settings()


def get_ai_provider(settings: Optional[Settings] = None):
    """Factory: build the configured AIProvider implementation.

    This is the single switch point referenced throughout the brief:
    "Switching providers should require changing only one
    configuration value." Callers never import a concrete provider
    class directly; they call this factory and depend on the
    `AIProvider` abstract interface.
    """
    settings = settings or get_settings()
    settings.validate()

    if settings.ai_provider == constants.PROVIDER_CLAUDE:
        from providers.claude_provider import ClaudeProvider

        return ClaudeProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_model,
            default_max_tokens=settings.claude_max_tokens,
        )

    # Default / fallback: mock provider. Deterministic, no network
    # access, no API key required - ideal for local dev, CI, and unit
    # tests.
    from providers.mock_provider import MockProvider

    return MockProvider()
