"""Classifies a raw value so the toolbox can decide which tools apply to it."""

from __future__ import annotations

import re

from shared.definitions.toolbox import InputKind
from shared.utils.validation import (
    normalize_domain,
    normalize_target_value,
    validate_target,
)

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


def classify(raw: str) -> tuple[str, str] | None:
    """Return the input kind and its normalised value, or None when unrecognised."""
    value = (raw or "").strip()
    if not value:
        return None
    if CVE_PATTERN.match(value):
        return InputKind.CVE.value, value.upper()
    target_type = validate_target(value)
    if target_type is None:
        return None
    kind = target_type.value
    if kind == InputKind.DOMAIN.value:
        return kind, normalize_domain(value)
    return kind, normalize_target_value(value)
