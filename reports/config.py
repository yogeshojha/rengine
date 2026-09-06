"""Field helpers for a section's config. The schema they produce is what the builder renders."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
