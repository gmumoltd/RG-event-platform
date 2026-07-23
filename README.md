# Event Platform

A modular, multi-agent AI platform that generates SEO-optimized event
landing pages from structured event data.

For a full explanation of the architecture, module responsibilities,
data flow, and extension guides, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) configure environment
cp .env.example .env
# Leave AI_PROVIDER=mock to run fully offline with no API key.

# 3. Run the pipeline
python main.py
```

This reads `data/events.json`, applies the rules in
`rules/event_rules.yaml`, runs each event through the
Content -> Image -> Linking agent pipeline, and writes the generated
site to `output/`:

```
output/
  concerts/nairobi-sunset-sessions.html
  conferences/east-africa-devcon.html
  webinars/scaling-saas-in-africa.html
  ...
  index.html        # site-wide listing page
  sitemap.xml
  robots.txt
```

Structured logs are written to `logs/app.log`, and per-agent AI
token usage is appended to `logs/token_usage.csv`.

## Switching to a live AI provider

Set the following in `.env` (or your environment) and re-run:

```
AI_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-5
```

No code changes are required - see `config/settings.get_ai_provider`.

## Running tests

```bash
pip install pytest
pytest tests/
```

## Adding a new event

Add an entry to `data/events.json` and, if it's a new `subtype`, add a
matching block to `rules/event_rules.yaml` (copy the `default` block
as a starting point) and a template in `templates/` if you want
subtype-specific markup.

## Project layout

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown. In
short:

| Folder | Responsibility |
|---|---|
| `agents/` | Thin pipeline steps: read/write `Context` only |
| `services/` | Business logic each agent delegates to |
| `providers/` | AI backends (mock / Claude), swappable via config |
| `core/` | `Context`, `AgentRegistry`, `PipelineRunner` |
| `models/` | Typed data (`Event`, `GeneratedContent`, `ImageData`, `LinkData`) |
| `assembler/` | Jinja2 HTML rendering |
| `seo/` | Meta tags, JSON-LD schema, sitemap/robots |
| `scraper/` | Image sourcing, decoupled from agents |
| `rules/` | YAML-driven SEO/content/image/linking rules per event subtype |
| `config/` | Environment-driven settings + static constants |
| `utils/` | Logging, file I/O, validation |
| `templates/` | Jinja2 page templates |
| `tests/` | Unit tests (services + orchestrator, using fakes) |
