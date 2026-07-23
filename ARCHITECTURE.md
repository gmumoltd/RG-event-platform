# Architecture

This document explains *why* the codebase is organized the way it is,
what each class is responsible for, how data moves through the
system, how to extend it, and how to branch/deploy it. It's written
for engineers picking this codebase up for the first time.

---

## 1. Why each folder exists

```
event-platform/
├── main.py            composition root - wires dependencies, no logic
├── config/             environment settings + static constants
├── core/               Context, AgentRegistry, PipelineRunner
├── models/              typed data: Event, GeneratedContent, ImageData, LinkData
├── providers/           AI backends (mock / Claude), behind one interface
├── services/            business logic: content, image, linking
├── agents/               thin pipeline steps that read/write Context only
├── assembler/           Jinja2 HTML rendering
├── seo/                  meta tags, JSON-LD schema, sitemap/robots
├── scraper/              image sourcing, decoupled from agents
├── rules/                event_rules.yaml - all SEO/content/image rules
├── data/                 sample input: events.json, taxonomy.json
├── templates/            Jinja2 templates
├── utils/                logging, file I/O, validation
├── output/               generated site (git-ignored)
├── logs/                 app.log, token_usage.csv (git-ignored)
└── tests/                unit tests using fakes/mocks, no I/O required
```

Each folder maps to exactly one layer of a **layered / clean
architecture**, and the dependency direction only ever points inward,
toward `models/` and `core/`:

```
agents/  --calls-->  services/  --calls-->  providers/  (interfaces)
   |                     |
   v                     v
core/context (shared)  models/ (typed data everyone shares)
```

- **`models/`** has zero dependencies on anything else in the
  project. It's pure data. Every other layer depends on it; it
  depends on nothing.
- **`providers/`** depends only on `models/`-level concepts (really,
  on nothing but the standard library and the `anthropic` SDK). It
  has no idea events, content sections, or SEO exist - it just turns
  a prompt into text.
- **`services/`** depends on `models/` and `providers/`. This is
  where business rules live (how a title is built, how related links
  are chosen). Services never import Jinja2, never touch the
  filesystem, never know an "agent" exists.
- **`agents/`** depend on `services/` and `core/context`. An agent is
  intentionally "dumb" - it has no business logic of its own. Its
  only job is: read `Context`, call one service, write the result
  back to `Context`.
- **`core/`** depends on `models/` and (for `pipeline.py`) on
  `agents/`, `services/`, `providers/`, and `assembler/` - it's the
  composition layer that assembles everything for a run.
- **`assembler/` and `seo/`** depend on `models/` and `core/context`
  only - they consume a finished `Context` and produce output
  (HTML, JSON-LD, sitemap entries). They never mutate `Context`.
- **`main.py`** depends on `config/` and `core/pipeline` only. It is
  the single "impure" entry point that's allowed to call
  `sys.exit()`; everything it calls is pure composition.

This separation is what satisfies the brief's SOLID/Clean
Architecture/DRY/KISS/Open-Closed requirements in practice, not just
as a checklist:

- **Single Responsibility** - each class in the list below does one
  thing (see section 2).
- **Open/Closed** - adding an agent, provider, or subtype rule never
  requires editing `Orchestrator`, `AIProvider` callers, or
  `HTMLBuilder`. You add a file/config entry, not a conditional.
- **Dependency Inversion** - `services/` and `agents/` depend on the
  `AIProvider` and `ImageScraper` *interfaces* (`providers/ai_provider.py`,
  `scraper/image_scraper.py`), never on `ClaudeProvider` or a
  concrete scraper directly. Concrete implementations are chosen once,
  in `config/settings.get_ai_provider()` and `core/pipeline.py`.
- **DRY** - SEO patterns, section lists, and alt-text templates exist
  in exactly one place: `rules/event_rules.yaml`. No agent or service
  hardcodes copy.

---

## 2. Responsibility of every class

### `models/` - typed data, no behavior beyond simple derived properties

| Class | Responsibility |
|---|---|
| `Event` (`models/event.py`) | Immutable representation of one source event. `from_dict()` validates and builds it from raw JSON. `slug_base` derives a URL-safe slug. |
| `GeneratedContent`, `ContentSection` (`models/content.py`) | SEO copy produced for one event: title tag, meta description, slug, H1, and rendered sections. |
| `ImageData` (`models/image.py`) | The hero image chosen for an event: filename, alt text, optional source URL/dimensions/license. |
| `LinkItem`, `LinkData` (`models/link.py`) | Related links, breadcrumbs, and internal navigation links for one event page. |

### `core/` - shared state and composition

| Class | Responsibility |
|---|---|
| `Context` (`core/context.py`) | The blackboard every agent reads/writes: `event`, `content`, `images`, `links`, `metadata`, plus `run_history`/`errors` for observability. Agents **never** call each other directly - they only touch `Context`. |
| `AgentRunRecord` | One agent's timing/token/error result, appended to `Context.run_history`. |
| `StepTimer` | Small context manager for timing a block of code. |
| `AgentRegistry` (`core/registry.py`) | Ordered `(name, agent)` pairs. Registration order = execution order. Rejects duplicate names at registration time. |
| `PipelineRunner` (`core/pipeline.py`) | The real orchestration logic for a full site build: loads events/rules, builds a fresh `Orchestrator` + `Context` per event, runs the pipeline, writes each page, then writes site-wide artifacts (listing page, sitemap, robots.txt). This is where the brief's "no business logic in main.py" rule pushed the logic to. |

### `providers/` - AI backends

| Class | Responsibility |
|---|---|
| `AIProvider` (abstract, `providers/ai_provider.py`) | Contract: `generate(prompt, system=None, max_tokens=...) -> AIResponse`. `AIUsage`/`AIResponse` are the shared value types every provider returns. |
| `MockProvider` | Deterministic, offline implementation. Default provider; used in tests, CI, and any environment without an API key. |
| `ClaudeProvider` | Live implementation backed by the Anthropic Python SDK (`anthropic.Anthropic(...).messages.create(...)`). |

### `services/` - business logic

| Class | Responsibility |
|---|---|
| `ContentService` | Builds `GeneratedContent` for an `Event`: formats the title/meta/slug from `rules[subtype].seo`, then calls the injected `AIProvider` once per configured section to write body copy. Returns content plus aggregated `AIUsage`. |
| `ImageService` | Builds `ImageData`: formats alt text from rules, asks the injected `ImageScraper` for candidates, asks `ImageSelector` to rank them, and falls back to a deterministic placeholder if nothing is found. |
| `LinkingService` | Builds `LinkData`: related events (same subtype, rule-capped count), breadcrumbs (Home / category / subtype / event), and internal navigation links. |

### `agents/` - thin pipeline steps

| Class | Responsibility |
|---|---|
| `BaseAgent` (abstract, `agents/base_agent.py`) | Defines the `run(context) -> context` contract subclasses implement, and provides `execute(context)` - a template method that times the call, catches and records any exception onto `Context` (so one failing agent doesn't crash the whole run), and reads back any `AIUsage` the agent recorded via `self._last_usage`. |
| `ContentAgent` | Calls `ContentService.generate(context.event)`, stores the result on `context.content`. |
| `ImageAgent` | Calls `ImageService.source_image(context.event)`, stores the result on `context.images`. |
| `LinkingAgent` | Reads `context.metadata["all_events"]`, calls `LinkingService.build_links(...)`, stores the result on `context.links`. |
| `Orchestrator` (`agents/orchestrator.py`) | Iterates every `(name, agent)` in its `AgentRegistry` and calls `agent.execute(context)` in order. Logs a summary (success/error count, token usage) at the end of each event's run. Contains **no knowledge** of what any individual agent does. |

### `assembler/` and `seo/` - output rendering

| Class/module | Responsibility |
|---|---|
| `HTMLBuilder` (`assembler/html_builder.py`) | Owns the Jinja2 `Environment`. `build_page(context)` picks the right template for the event's subtype (from rules) and renders it with meta/OG/Twitter/schema data. `build_listing_page(contexts)` renders the site index. |
| `seo/metadata.py` | Pure functions: `build_meta_tags`, `build_open_graph_tags`, `build_twitter_card_tags`, `build_canonical_url`. |
| `seo/schema.py` | Pure functions: `build_event_schema` (dict) / `build_event_schema_json` (string) - schema.org `Event` JSON-LD. |
| `seo/sitemap.py` | `build_sitemap_xml(contexts, base_url)`, `build_robots_txt(base_url)` - operate over *all* contexts from one run, not a single event. |

### `scraper/` - image sourcing, decoupled from agents

| Class | Responsibility |
|---|---|
| `ImageScraper` (abstract) | Contract: `search(query, limit) -> list[ImageCandidate]`. |
| `NullImageScraper` | Default: returns no candidates (no network access required). `ImageService` falls back to a placeholder when this is used. |
| `StaticImageScraper` | Looks candidates up from an in-memory dict - useful for tests/offline demos with a fixed image catalogue. |
| `ImageSelector` (`scraper/selector.py`) | Pure ranking logic: picks the highest-resolution candidate that meets a configurable minimum size, or the largest available if none do. |

### `utils/` and `config/`

| Class/module | Responsibility |
|---|---|
| `get_logger()` / `TokenUsageLogger` (`utils/logger.py`) | Structured app logging (console + `logs/app.log`, plain-text or JSON) and a CSV token-usage log (`logs/token_usage.csv`), one row per agent execution. |
| `file_manager.py` | The only module that calls `open()`/`Path.write_text()` directly for input/output data. |
| `validator.py` | Validates the raw `events.json` array and the parsed `rules` dict at the system boundary, so downstream code can trust the shapes it receives. |
| `Settings` (`config/settings.py`) | Frozen dataclass of every environment-driven value (`AI_PROVIDER`, `CLAUDE_API_KEY`, `BASE_URL`, ...). `validate()` fails fast on bad config. `get_ai_provider(settings)` is the **one** factory function that decides which `AIProvider` concrete class to build. |
| `constants.py` (`config/constants.py`) | Static values that never change per environment: file paths, fallback rule/template names, schema.org constants. |

---

## 3. How data flows through the system

**One event, end to end:**

```
data/events.json (raw dict)
        │  Event.from_dict()          [models/event.py]
        ▼
     Event
        │
        ▼
Context(event=Event, metadata={"all_events": [...]})   [core/context.py]
        │
        ▼
Orchestrator.run(context)                                [agents/orchestrator.py]
        │
        ├─▶ ContentAgent.execute(context)
        │       └─▶ ContentService.generate(event)          [services/content_service.py]
        │               ├─ formats title/meta/slug from rules[subtype].seo
        │               └─ calls AIProvider.generate(...) per rules[subtype].content.sections
        │           → context.content = GeneratedContent
        │
        ├─▶ ImageAgent.execute(context)
        │       └─▶ ImageService.source_image(event)         [services/image_service.py]
        │               ├─ formats alt text from rules[subtype].images
        │               ├─ ImageScraper.search(query) → ImageCandidate[]
        │               └─ ImageSelector.select_best(candidates)
        │           → context.images = ImageData
        │
        └─▶ LinkingAgent.execute(context)
                └─▶ LinkingService.build_links(event, all_events)  [services/linking_service.py]
                        ├─ related events (same subtype, rule-capped)
                        ├─ breadcrumbs (Home / category / subtype / event)
                        └─ internal nav links
                    → context.links = LinkData
        │
        ▼
context now fully populated: event, content, images, links, run_history
        │
        ▼
HTMLBuilder.build_page(context)                            [assembler/html_builder.py]
        ├─ seo.metadata.build_meta_tags / og / twitter / canonical_url
        ├─ seo.schema.build_event_schema_json
        └─ Jinja2 template render (rules[subtype].template)
        ▼
output/<slug>.html
```

**After every event in the run has been processed:**

```
List[Context]
        │
        ├─▶ HTMLBuilder.build_listing_page(contexts) → output/index.html
        ├─▶ seo.sitemap.build_sitemap_xml(contexts)   → output/sitemap.xml
        └─▶ seo.sitemap.build_robots_txt(base_url)    → output/robots.txt
```

At every step, agents communicate **only** by reading and writing
fields on the same `Context` object - never by importing or calling
each other. That is what allows `Orchestrator` to run any subset or
ordering of agents without modification.

---

## 4. How to add a new agent

Say you want a `FaqAgent` that generates an FAQ block after linking.

1. **Add a service** (if it has real logic) in `services/faq_service.py`,
   depending only on `models/` and, if it needs AI, on `AIProvider`.
2. **Add a model** in `models/faq.py` if the output is structured data
   (e.g. `FaqData` with a list of Q&A pairs).
3. **Add a field to `Context`** in `core/context.py`:
   `faq: Optional[FaqData] = None`.
4. **Add the agent** in `agents/faq_agent.py`, subclassing `BaseAgent`:

   ```python
   class FaqAgent(BaseAgent):
       name = "FaqAgent"

       def __init__(self, faq_service: FaqService) -> None:
           super().__init__()
           self._faq_service = faq_service

       def run(self, context: Context) -> Context:
           context.faq = self._faq_service.generate(context.event, context.content)
           return context
   ```

5. **Register it** - the only change to existing code, in
   `core/pipeline.py`'s `_build_orchestrator()`:

   ```python
   registry.register("faq", FaqAgent(self._faq_service))
   ```

`Orchestrator` itself needs **zero** changes. If `FaqAgent` should
also influence the rendered page, add the corresponding block to
`templates/base.html` (or a subtype template) and reference
`context.faq` there.

---

## 5. How to add a new AI provider

Say you want an `OpenAIProvider`.

1. Create `providers/openai_provider.py`:

   ```python
   from providers.ai_provider import AIProvider, AIResponse, AIUsage

   class OpenAIProvider(AIProvider):
       def __init__(self, api_key: str, model: str) -> None:
           ...

       def generate(self, prompt, *, system=None, max_tokens=1024) -> AIResponse:
           # call the OpenAI SDK, map its usage fields into AIUsage
           ...
   ```

2. Add its identifier to `config/constants.py`:

   ```python
   PROVIDER_OPENAI = "openai"
   SUPPORTED_PROVIDERS = (PROVIDER_MOCK, PROVIDER_CLAUDE, PROVIDER_OPENAI)
   ```

3. Add one branch to the factory in `config/settings.py`:

   ```python
   if settings.ai_provider == constants.PROVIDER_OPENAI:
       from providers.openai_provider import OpenAIProvider
       return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
   ```

4. Set `AI_PROVIDER=openai` (plus whatever credentials it needs) in
   `.env`.

No changes to `ContentService`, `ImageService`, any agent, or
`Orchestrator` are required - they all depend on the `AIProvider`
interface, never on a concrete class.

---

## 6. Git branching strategy

Recommended for a small-to-medium team shipping continuously:

- **`main`** - always deployable. Every commit on `main` is (or came
  from) a released state. Protected: no direct pushes, PR + at least
  one review + passing CI required.
- **`develop`** - integration branch. Feature branches merge here
  first; `develop` is what a staging environment deploys from.
- **`feature/<short-description>`** - one branch per unit of work
  (e.g. `feature/faq-agent`, `feature/openai-provider`), branched from
  `develop`, merged back via PR, deleted after merge.
- **`fix/<short-description>`** - same as `feature/`, for bug fixes
  that aren't urgent hotfixes.
- **`hotfix/<short-description>`** - branched from `main` for
  production-breaking fixes, merged into both `main` and `develop`,
  tagged and released immediately.
- **Releases** - tag `main` with semantic versions (`v1.2.0`) at each
  deploy. Squash-merge feature branches so `main`/`develop` history
  stays one commit per feature.

Commit messages: conventional commits (`feat:`, `fix:`, `refactor:`,
`docs:`, `test:`) make it trivial to auto-generate changelogs and
keep the intent of each change legible - something the original
prototype's history (`"Ipmlement AI provider abstraction"`,
`"corrections on the file path"`) shows the value of doing
consistently from day one.

CI on every PR should run `pytest tests/` and a lint/type check
(e.g. `ruff` + `mypy`) before merge is allowed.

---

## 7. How to deploy

The platform's output is a **static site** (`output/*.html`,
`sitemap.xml`, `robots.txt`, plus `images/`) - it has no runtime
server component of its own. Deployment is therefore a two-stage
pipeline: *build*, then *publish the static output*.

### Recommended CI/CD flow

1. **Build stage** (runs on every merge to `main`, or on a schedule if
   `data/events.json` is refreshed from an external source):

   ```bash
   pip install -r requirements.txt
   export AI_PROVIDER=claude
   export CLAUDE_API_KEY=${SECRET_CLAUDE_API_KEY}
   export BASE_URL=https://your-production-domain.com
   python main.py
   ```

   Fail the pipeline if `main.py` exits non-zero, or if
   `PipelineRunner` reports any event with errors (check
   `logs/app.log` / the `errors` field on each `Context` - wire a
   simple assertion in a small CI script if you want a hard gate).

2. **Publish stage** - upload the contents of `output/` to any static
   host:
   - **Static hosting**: Netlify, Vercel (static export), Cloudflare
     Pages, GitHub Pages, or an S3 bucket + CloudFront distribution.
   - **Traditional**: rsync `output/` to an Nginx/Apache document
     root.

   Example (S3 + CloudFront):

   ```bash
   aws s3 sync output/ s3://your-bucket/ --delete
   aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
   ```

3. **Secrets**: `CLAUDE_API_KEY` must be injected via your CI
   platform's secret store (GitHub Actions secrets, GitLab CI/CD
   variables, etc.) - never committed. `.env` is for local development
   only and should stay in `.gitignore`.

4. **Environments**: use different `.env` values per environment
   (`BASE_URL`, `SITE_NAME`) so staging builds get correct canonical
   URLs/sitemaps distinct from production. `AI_PROVIDER=mock` is a
   sensible default for a staging/preview build if you want to avoid
   burning API tokens on every PR preview.

5. **Scaling the generation step itself**: `PipelineRunner.run_all()`
   processes events sequentially. For a large event catalogue, the
   per-event loop in `core/pipeline.py` is the one place to introduce
   concurrency (e.g. a thread pool around `orchestrator.run(context)`
   per event) without touching agents, services, or providers -
   each event's `Context` is already fully independent of every
   other event's.

### Suggested `.gitignore`

```
__pycache__/
*.pyc
.env
output/
logs/*.log
logs/token_usage.csv
```

(`output/` and `logs/` are regenerated by every build; they don't
belong in version control.)
