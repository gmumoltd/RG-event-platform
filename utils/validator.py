"""
utils/validator.py
---------------------
Validation at the system's input boundaries: the raw events file and
the raw rules file. Validating here means every downstream module
(services, agents) can trust that an `Event` or a rules dict is
well-formed, instead of re-checking the same things everywhere.
"""

from __future__ import annotations

from typing import Any, Dict, List


class ValidationError(ValueError):
    """Raised when input data fails validation."""


def validate_raw_events(raw_events: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_events, list):
        raise ValidationError(f"data/events.json must contain a JSON array, got {type(raw_events).__name__}")

    if not raw_events:
        raise ValidationError("data/events.json contains no events.")

    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            raise ValidationError(f"Event at index {index} is not an object: {raw!r}")
        if not str(raw.get("name", "")).strip():
            raise ValidationError(f"Event at index {index} is missing a non-empty 'name'.")

    return raw_events


def validate_rules(rules: Any) -> Dict[str, Any]:
    if not isinstance(rules, dict) or not rules:
        raise ValidationError("rules/event_rules.yaml must contain a non-empty mapping of subtype -> rules.")

    if "default" not in rules:
        raise ValidationError("rules/event_rules.yaml must define a 'default' rule set as a fallback.")

    for subtype, subtype_rules in rules.items():
        if not isinstance(subtype_rules, dict):
            raise ValidationError(f"Rules for subtype '{subtype}' must be a mapping.")
        for required_section in ("seo", "content", "images"):
            if required_section not in subtype_rules:
                raise ValidationError(f"Rules for subtype '{subtype}' are missing required section '{required_section}'.")

    return rules
