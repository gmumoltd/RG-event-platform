"""
scraper/selector.py
---------------------
Chooses the best candidate from a list of `ImageCandidate`s.

Split out from `image_scraper.py` so the *sourcing* of candidates
(network calls, API clients) and the *ranking* of candidates (pure
business logic) can change, and be tested, independently. The
selector has no I/O and no external dependencies - it's a pure
function wrapped in a small class for consistency with the rest of
the codebase.
"""

from __future__ import annotations

from typing import List, Optional

from scraper.image_scraper import ImageCandidate


class ImageSelector:
    """Ranks candidates by resolution and rule-defined minimums."""

    def __init__(self, min_width: int = 800, min_height: int = 450) -> None:
        self.min_width = min_width
        self.min_height = min_height

    def select_best(self, candidates: List[ImageCandidate]) -> Optional[ImageCandidate]:
        if not candidates:
            return None

        eligible = [
            c
            for c in candidates
            if (c.width or 0) >= self.min_width and (c.height or 0) >= self.min_height
        ] or candidates  # fall back to the full list if nothing meets the minimum

        return max(eligible, key=lambda c: (c.width or 0) * (c.height or 0))
