"""The Jinja environment: section templates plus the filters they all use."""

from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

from reports.charts import bars, cover_art, dial, donut, matrix, sparkline, stack_bar
from reports.charts.svg import Slice
from reports.render.media import image_data_uri
from shared.definitions.ports import SERVICE_CLASS_LABELS
from shared.definitions.vulnerabilities import SEVERITY_LABELS

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
SECTIONS = Path(__file__).resolve().parent.parent / "sections"

_MD = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": True})
_MD.enable("table")
_MD.enable("strikethrough")

_REMOTE_IMG = re.compile(r"<img\b[^>]*?src=[\"\']((?!data:)[^\"\']*)[\"\'][^>]*>", re.I)

_MINUTE = 60
_HOUR = 3600


def markdown(value: str | None) -> str:
    """Authored text may embed an image, never link one, so nothing here can be fetched."""
    return _REMOTE_IMG.sub("", _MD.render(value or "")).strip()


def number(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.1f}"


def percent(value: float | None, *, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}%"


def share(part: float | None, whole: float | None, *, digits: int = 0) -> str:
    if not whole:
        return "—"
    return percent((part or 0) / whole, digits=digits)


def date(value: datetime | None, fmt: str = "%d %B %Y") -> str:
    return value.strftime(fmt) if value else "—"


def datetime_at(value: datetime | None) -> str:
    return value.strftime("%d %b %Y, %H:%M UTC") if value else "—"


def duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = int(seconds)
    if total < _MINUTE:
        return f"{total}s"
    if total < _HOUR:
        return f"{total // 60}m {total % 60:02d}s"
    return f"{total // 3600}h {(total % 3600) // 60:02d}m"


def clip(value: str | None, length: int = 80) -> str:
    """Trim, and drop the replacement character a bad byte upstream leaves behind."""
    text = (value or "").replace("\ufffd", "")
    return text if len(text) <= length else text[: length - 1] + "…"


def severity_label(value: str | None) -> str:
    return SEVERITY_LABELS.get((value or "").lower(), "Unknown")


def service_label(value: str | None) -> str:
    return SERVICE_CLASS_LABELS.get((value or "").lower(), "Other")


def plural(count: int, word: str, suffix: str = "s") -> str:
    return word if count == 1 else f"{word}{suffix}"


def counted(count: int, word: str, suffix: str = "s") -> str:
    return f"{number(count)} {plural(count, word, suffix)}"


def pairs(rows) -> list[tuple[str, float]]:
    return [(getattr(r, "name", ""), getattr(r, "count", 0)) for r in rows]


def severity_fill(value: str | None) -> str:
    return f"var(--r-sev-{(value or 'unknown').lower()})"


def chart_fill(index: int) -> str:
    return f"var(--r-chart-{(index % 8) + 1})"


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
            "pct": percent,
            "share": share,
            "date": date,
            "at": datetime_at,
            "dur": duration,
            "clip": clip,
            "sev": severity_label,
            "svc": service_label,
            "plural": plural,
            "counted": counted,
            "sevfill": severity_fill,
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
            "matrix": matrix,
            "cover_art": cover_art,
            "chart_fill": chart_fill,
            "severity_fill": severity_fill,
        }
    )
    return env
