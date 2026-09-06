"""The one place the renderer is allowed to load bytes from. Everything else is refused."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from shared.logging import get_logger

logger = get_logger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
CUSTOM_FONTS = Path("/app/report-fonts")
SCAN_MEDIA = Path("/app/scan_media")

# a rendered document may read vendored faces, uploaded faces and captured screenshots
ALLOWED_ROOTS: tuple[Path, ...] = (ASSETS, CUSTOM_FONTS, SCAN_MEDIA)
ALLOWED_PROTOCOLS: tuple[str, ...] = ("data", "file")


class BlockedResourceError(ValueError):
    """The document asked for something outside the allowed roots."""


def _allowed(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return any(resolved.is_relative_to(root) for root in ALLOWED_ROOTS)


def permitted(url: str) -> bool:
    """Data URIs, and files under a known root. No network, ever."""
    if url.startswith("data:"):
        return True
    if not url.startswith("file:"):
        return False
    parsed = urlparse(url)
    if parsed.netloc not in ("", "localhost"):
        return False
    return _allowed(Path(unquote(parsed.path)))


def build_fetcher():
    """A WeasyPrint fetcher that cannot reach the network, whatever the document asks for."""
    from weasyprint.urls import URLFetcher  # noqa: PLC0415

    class SafeFetcher(URLFetcher):
        def fetch(self, url, headers=None):
            if not permitted(url):
                logger.warning("report blocked a resource", url=url[:200])
                msg = (
                    "A report may only load embedded data and files shipped with the "
                    f"instance. Refused: {url[:120]}"
                )
                raise BlockedResourceError(msg)
            return super().fetch(url, headers)

    return SafeFetcher(timeout=5, allowed_protocols=ALLOWED_PROTOCOLS)
