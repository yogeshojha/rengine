"""The Jinja environment: section templates plus the filters they all use."""

from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

from reports.charts import bars, cover_art, dial, donut, sparkline, stack_bar
from reports.charts.svg import Slice
from reports.render.media import image_data_uri
from shared.definitions.ports import SERVICE_CLASS_LABELS
from shared.definitions.vulnerabilities import SEVERITY_LABELS
from shared.utils import text as text_utils

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
SECTIONS = Path(__file__).resolve().parent.parent / "sections"

_MD = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": True})
_MD.enable("table")
_MD.enable("strikethrough")

_REMOTE_IMG = re.compile(r"<img\b[^>]*?src=[\"\']((?!data:)[^\"\']*)[\"\'][^>]*>", re.I)


def markdown(value: str | None) -> str:
    """Render Markdown and drop images that are not data URIs."""
    return _REMOTE_IMG.sub("", _MD.render(value or "")).strip()


def number(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.1f}"


def date(value: datetime | None, fmt: str = "%d %B %Y") -> str:
    return value.strftime(fmt) if value else "—"


def datetime_at(value: datetime | None) -> str:
    return value.strftime("%d %b %Y, %H:%M UTC") if value else "—"


def clip(value: str | None, length: int = 80) -> str:
    """Trim to length and drop U+FFFD."""
    return text_utils.clip((value or "").replace("\ufffd", ""), length)


def severity_label(value: str | None) -> str:
    return SEVERITY_LABELS.get((value or "").lower(), "Unknown")


def service_label(value: str | None) -> str:
    return SERVICE_CLASS_LABELS.get((value or "").lower(), "Other")


def plural(count: int, word: str, suffix: str = "s") -> str:
    return word if count == 1 else f"{word}{suffix}"


def pairs(rows) -> list[tuple[str, float]]:
    return [(getattr(r, "name", ""), getattr(r, "count", 0)) for r in rows]


@lru_cache(maxsize=1)
def environment() -> Environment:
    env = Environment(
        loader=ChoiceLoader([FileSystemLoader(TEMPLATES), FileSystemLoader(SECTIONS)]),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        {
            "md": markdown,
            "num": number,
            "date": date,
            "at": datetime_at,
            "clip": clip,
            "sev": severity_label,
            "svc": service_label,
            "plural": plural,
            "pairs": pairs,
            "shot": image_data_uri,
        }
    )
    env.globals.update(
        {
            "Slice": Slice,
            "donut": donut,
            "bars": bars,
            "stack_bar": stack_bar,
            "dial": dial,
            "sparkline": sparkline,
            "cover_art": cover_art,
        }
    )
    return env
