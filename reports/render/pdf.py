"""WeasyPrint is imported here and nowhere else, so the api can read the catalog without it."""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass, field

from shared.definitions.reports import MAX_IMAGE_PIXELS


@dataclass
class PdfResult:
    data: bytes
    pages: int
    warnings: list[str] = field(default_factory=list)


# a warning about an embedded image must not repeat the whole image
_DATA_URI = re.compile(r"data:([\w./+-]+);base64,[A-Za-z0-9+/=]+")


class _Collector(logging.Handler):
    """WeasyPrint reports a dropped image or a missing face here; a report should say so."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        text = _DATA_URI.sub(
            lambda m: f"{m.group(1)} data, {len(m.group(0)) // 1024} KB",
            record.getMessage(),
        )
        text = text[:300]
        if text not in self.messages:
            self.messages.append(text)


@contextmanager
def render_limits():
    """A small image may decode to a huge canvas, so the ceiling is on pixels, not bytes."""
    from PIL import Image  # noqa: PLC0415

    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    weasy = logging.getLogger("weasyprint")
    collector = _Collector()
    weasy.addHandler(collector)
    try:
        yield collector
    finally:
        weasy.removeHandler(collector)
        Image.MAX_IMAGE_PIXELS = previous


def to_pdf(html: str, *, base_url: str) -> PdfResult:
    from weasyprint import HTML  # noqa: PLC0415

    from reports.render.fetcher import build_fetcher  # noqa: PLC0415

    with render_limits() as collected:
        document = HTML(
            string=html, base_url=base_url, url_fetcher=build_fetcher()
        ).render()
        data = document.write_pdf()
        pages = len(document.pages)
    return PdfResult(data=data, pages=pages, warnings=list(collected.messages))
