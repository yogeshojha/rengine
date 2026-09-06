"""WeasyPrint is imported here and nowhere else, so the api can read the catalog without it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PdfResult:
    data: bytes
    pages: int


def to_pdf(html: str, *, base_url: str) -> PdfResult:
    from weasyprint import HTML  # noqa: PLC0415

    from reports.render.fetcher import safe_url_fetcher  # noqa: PLC0415

    document = HTML(
        string=html, base_url=base_url, url_fetcher=safe_url_fetcher
    ).render()
    return PdfResult(data=document.write_pdf(), pages=len(document.pages))
