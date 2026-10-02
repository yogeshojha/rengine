"""Field helpers for a section's config."""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_CHANGE_ITEMS = 200


def text(
    default: str = "", *, title: str, description: str = "", max_length: int = 500
) -> Any:
    return Field(default, max_length=max_length, title=title, description=description)


def paragraph(
    default: str = "", *, title: str, description: str = "", max_length: int = 20_000
) -> Any:
    return Field(
        default,
        max_length=max_length,
        title=title,
        description=description,
        json_schema_extra={"widget": "markdown"},
    )


def flag(default: bool, *, title: str, description: str = "") -> Any:
    return Field(default, title=title, description=description)


def limit(
    default: int,
    *,
    title: str,
    description: str = "",
    minimum: int = 0,
    maximum: int = 5000,
) -> Any:
    return Field(default, ge=minimum, le=maximum, title=title, description=description)


def choice(
    default: str, *, title: str, options: dict[str, str], description: str = ""
) -> Any:
    return Field(
        default,
        max_length=60,
        title=title,
        description=description,
        json_schema_extra={
            "widget": "choice",
            "options": [{"value": k, "label": v} for k, v in options.items()],
        },
    )


def multi(
    default: list[str], *, title: str, options: dict[str, str], description: str = ""
) -> Any:
    return Field(
        default_factory=lambda: list(default),
        title=title,
        description=description,
        json_schema_extra={
            "widget": "multi",
            "options": [{"value": k, "label": v} for k, v in options.items()],
        },
    )


def columns(
    default: list[str], *, title: str, options: dict[str, str], description: str = ""
) -> Any:
    return Field(
        default_factory=lambda: list(default),
        title=title,
        description=description,
        json_schema_extra={
            "widget": "columns",
            "options": [{"value": k, "label": v} for k, v in options.items()],
        },
    )


class SectionConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    @model_validator(mode="after")
    def _in_options(self) -> Self:
        for name, field in type(self).model_fields.items():
            extra = field.json_schema_extra
            if not isinstance(extra, dict) or extra.get("widget") not in (
                "choice",
                "multi",
            ):
                continue
            allowed = [o["value"] for o in extra.get("options", [])]
            value = getattr(self, name)
            picked = value if isinstance(value, list) else [value]
            if any(v not in allowed for v in picked):
                msg = f"{field.title or name} must be one of {', '.join(allowed)}."
                raise ValueError(msg)
        return self
