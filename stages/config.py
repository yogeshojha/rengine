from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from shared.definitions.constants import MAX_RATE, MAX_THREADS, MAX_TIMEOUT


class Scale(StrEnum):
    THREADS = "threads"
    TIMEOUT = "timeout"
    RATE = "rate"


def threads(default: int, *, title: str, description: str = "") -> Any:
    return Field(
        default,
        ge=1,
        le=MAX_THREADS,
        title=title,
        description=description,
        json_schema_extra={"scale": Scale.THREADS.value},
    )


def timeout(default: int, *, title: str, description: str = "") -> Any:
    return Field(
        default,
        ge=1,
        le=MAX_TIMEOUT,
        title=title,
        description=description,
        json_schema_extra={"scale": Scale.TIMEOUT.value},
    )


def rate(default: int, *, tool: str, title: str, description: str = "") -> Any:
    return Field(
        default,
        ge=1,
        le=MAX_RATE,
        title=title,
        description=description,
        json_schema_extra={"scale": Scale.RATE.value, "tool": tool},
    )


class StageConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    enabled: bool = Field(
        default=True, title="Enabled", description="Run this stage during a scan."
    )

    @classmethod
    def scaled_fields(cls) -> dict[str, tuple[Scale, str | None]]:
        out: dict[str, tuple[Scale, str | None]] = {}
        for name, field in cls.model_fields.items():
            extra = field.json_schema_extra
            if not isinstance(extra, dict) or "scale" not in extra:
                continue
            out[name] = (Scale(extra["scale"]), extra.get("tool"))
        return out

    @classmethod
    def rate_tools(cls) -> set[str]:
        return {
            tool for scale, tool in cls.scaled_fields().values() if scale is Scale.RATE and tool
        }
