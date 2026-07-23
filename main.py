"""
main.py
--------
Composition root. This file's only job is to wire dependencies
together and start the pipeline - it contains no business logic
(no SEO rules, no HTML rendering, no event parsing). If you find
yourself adding an `if`/`for` that touches event data here, that
logic almost certainly belongs in `core/pipeline.py`,  a service, or
an agent instead.
"""

from __future__ import annotations

import sys

from config.settings import get_ai_provider, get_settings
from core.pipeline import PipelineRunner
from utils.logger import get_logger

logger = get_logger("main")


def main() -> int:
    settings = get_settings()

    try:
        settings.validate()
        ai_provider = get_ai_provider(settings)
        runner = PipelineRunner(settings=settings, ai_provider=ai_provider)
        contexts = runner.run_all()
    except Exception as exc:  # noqa: BLE001 - top-level guard, log and exit non-zero
        logger.error("Pipeline run failed: %s", exc)
        return 1

    failed = [c for c in contexts if c.has_errors]
    if failed:
        logger.warning("%d of %d event(s) completed with errors - see logs/app.log for details.", len(failed), len(contexts))

    return 0


if __name__ == "__main__":
    sys.exit(main())
