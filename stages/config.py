from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from shared.definitions.wordlists import DEFAULT_WORDLIST, MAX_SLUG_LENGTH


class FieldTier(StrEnum):
    BASIC = "basic"
    ADVANCED = "advanced"


class FieldNeeds(StrEnum):
    """Instance configuration a field is inert without."""

    OAST = "oast"


ADVANCED: dict[str, str] = {"tier": FieldTier.ADVANCED.value}


def advanced(default: Any = None, **kwargs: Any) -> Any:
    """A field behind the stage's Advanced disclosure."""
    extra = dict(kwargs.pop("json_schema_extra", None) or {})
    extra.update(ADVANCED)
    if "default_factory" in kwargs:
        return Field(json_schema_extra=extra, **kwargs)
    return Field(default, json_schema_extra=extra, **kwargs)


def wordlist(kind: str, *, title: str, description: str = "") -> Any:
    """A named list from the library."""
    return Field(
        DEFAULT_WORDLIST[kind],
        max_length=MAX_SLUG_LENGTH,
        title=title,
        description=description,
        json_schema_extra={"widget": "wordlist", "kind": kind},
    )


def share_rate(rate: int, processes: int) -> int:
    """One process's share of the stage's rate budget."""
    return max(1, rate // max(1, processes))


class StageConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    enabled: bool = Field(
        default=True, title="Enabled", description="Run this stage during a scan."
    )

    @classmethod
    def tiers(cls) -> dict[str, str]:
        out: dict[str, str] = {}
        for name, field in cls.model_fields.items():
            extra = field.json_schema_extra
            tier = extra.get("tier") if isinstance(extra, dict) else None
            out[name] = tier or FieldTier.BASIC.value
        return out
