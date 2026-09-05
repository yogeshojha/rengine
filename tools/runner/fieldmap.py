from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from shared.utils.text import scrub


@dataclass(frozen=True)
class F:
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
        value = scrub(value)
        if self.max_len is not None and isinstance(value, str):
            value = value[: self.max_len]
        return value


def parse_record(record: dict, fieldmap: dict[str, F]) -> dict[str, Any]:
    return {field: spec.extract(record) for field, spec in fieldmap.items()}
