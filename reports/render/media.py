"""Images are embedded, so a PDF and a standalone HTML file both carry their evidence."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

MEDIA_ROOT = Path("/app/scan_media")
_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
_MAX_BYTES = 3_000_000


@lru_cache(maxsize=256)
def image_data_uri(path: str | None) -> str:
    if not path:
        return ""
    candidate = (MEDIA_ROOT / path).resolve()
    if not candidate.is_relative_to(MEDIA_ROOT) or not candidate.is_file():
        return ""
    media_type = _TYPES.get(candidate.suffix.lower())
    if media_type is None or candidate.stat().st_size > _MAX_BYTES:
        return ""
    encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"
