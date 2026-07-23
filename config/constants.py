"""
config/constants.py
--------------------
Static, environment-independent constants for the platform.

These values never change between deployments. Anything that *does*
change between environments (API keys, base URLs, feature flags)
belongs in `config/settings.py` instead, sourced from environment
variables. Keeping the two separated means a developer can scan this
file to understand fixed business rules without wondering whether a
value might be overridden by `.env`.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Filesystem layout (all paths are relative to the project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RULES_PATH = PROJECT_ROOT / "rules" / "event_rules.yaml"
EVENTS_PATH = PROJECT_ROOT / "data" / "events.json"
TAXONOMY_PATH = PROJECT_ROOT / "data" / "taxonomy.json"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"
IMAGES_DIR = PROJECT_ROOT / "images"
LOGS_DIR = PROJECT_ROOT / "logs"

TOKEN_USAGE_LOG_PATH = LOGS_DIR / "token_usage.csv"
APP_LOG_PATH = LOGS_DIR / "app.log"

# ---------------------------------------------------------------------------
# Domain defaults
# ---------------------------------------------------------------------------
DEFAULT_SUBTYPE = "default"
DEFAULT_CATEGORY = "general"

# Fallback rule set used whenever an event's subtype has no entry in
# rules/event_rules.yaml. Keeps the pipeline from crashing on
# unexpected/unknown subtypes while still producing a usable page.
FALLBACK_RULE_KEY = "default"

# HTML template used when a subtype has no dedicated template mapped
# in the rules file.
FALLBACK_TEMPLATE = "base.html"

# ---------------------------------------------------------------------------
# SEO defaults
# ---------------------------------------------------------------------------
DEFAULT_LOCALE = "en_US"
DEFAULT_TWITTER_CARD_TYPE = "summary_large_image"
SCHEMA_CONTEXT = "https://schema.org"
SCHEMA_EVENT_TYPE = "Event"

# ---------------------------------------------------------------------------
# Provider identifiers (used by config.settings.get_ai_provider factory)
# ---------------------------------------------------------------------------
PROVIDER_MOCK = "mock"
PROVIDER_CLAUDE = "claude"
SUPPORTED_PROVIDERS = (PROVIDER_MOCK, PROVIDER_CLAUDE)
