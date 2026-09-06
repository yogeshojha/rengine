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


class BlockedResourceError(ValueError):
    """The document asked for something outside the allowed roots."""


def _allowed(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return any(resolved.is_relative_to(root) for root in ALLOWED_ROOTS)


def safe_url_fetcher(url: str, *args, **kwargs):
    """Data URIs and files under a known root. No network, ever."""
    from weasyprint.urls import default_url_fetcher  # noqa: PLC0415

    if url.startswith("data:"):
        return default_url_fetcher(url, *args, **kwargs)

    if url.startswith("file:"):
        parsed = urlparse(url)
        if parsed.netloc not in ("", "localhost"):
            msg = f"Refused a remote file reference: {url[:120]}"
            raise BlockedResourceError(msg)
        if _allowed(Path(unquote(parsed.path))):
            return default_url_fetcher(url, *args, **kwargs)

    logger.warning("report blocked a resource", url=url[:200])
    msg = (
        "A report may only load embedded data and files shipped with the instance. "
        f"Refused: {url[:120]}"
    )
    raise BlockedResourceError(msg)
