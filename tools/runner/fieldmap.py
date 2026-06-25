"""Declarative field mapping — the single source of truth for turning a tool's
JSON record into model-ready fields.

Each tool defines ONE map of `{model_field: F(...)}`. Adding/renaming/retyping a
field a tool emits is a one-line edit there; nothing else changes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class F:
    """One field rule.

    src: a JSON key, a dotted path ("tls.not_after"), or a getter(record).
    cast: optional coercion applied when the value is not None.
    max_len: optional truncation for string values.
    """

    src: str | Callable[[dict], Any]
    cast: Callable[[Any], Any] | None = None
    max_len: int | None = None

    def extract(self, record: dict) -> Any:
        if callable(self.src):
            value = self.src(record)
        else:
            value: Any = record
            for part in self.src.split("."):
                value = value.get(part) if isinstance(value, dict) else None
        if value is not None and self.cast is not None:
            value = self.cast(value)
        if self.max_len is not None and isinstance(value, str):
            value = value[: self.max_len]
        return value


def parse_record(record: dict, fieldmap: dict[str, F]) -> dict[str, Any]:
    """Apply a field map to one record -> {model_field: value}."""
    return {field: spec.extract(record) for field, spec in fieldmap.items()}
