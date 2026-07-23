"""
models/event.py
----------------
Strongly typed representation of the source data. Replaces the raw
`dict` that the original prototype passed between functions
(`event["name"]`, `event.get("subtype")`, ...). Typed models give us:

- IDE autocomplete and static-analysis support
- A single, documented place that defines what an "event" is
- Validation at the boundary (`from_dict`) instead of scattered
  `KeyError` crashes deep inside services
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional

from config.constants import DEFAULT_CATEGORY, DEFAULT_SUBTYPE


@dataclass(frozen=True, slots=True)
class Event:
    """A single event to generate a landing page for."""

    name: str
    subtype: str = DEFAULT_SUBTYPE
    category: str = DEFAULT_CATEGORY
    location: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    organizer: Optional[str] = None
    website: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def slug_base(self) -> str:
        """A filesystem/URL-safe base slug derived from the name.

        Individual rule sets may still apply their own
        `slug_pattern`; this is the raw fallback building block they
        can format around (see rules/event_rules.yaml).
        """
        return "-".join(self.name.strip().lower().split())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Build an Event from a raw dict (e.g. parsed JSON).

        Unknown keys are ignored rather than raising, so the source
        data file can carry extra editorial fields without breaking
        the pipeline. Missing required fields raise a clear
        `ValueError` instead of a `KeyError` several call-frames away.
        """
        if "name" not in data or not str(data["name"]).strip():
            raise ValueError(f"Event is missing a required 'name' field: {data!r}")

        known_fields = {f.name for f in fields(cls)}
        clean = {k: v for k, v in data.items() if k in known_fields}
        return cls(**clean)
