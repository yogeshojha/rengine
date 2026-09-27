from __future__ import annotations

from pathlib import Path

KEEP_FOREVER = 0

SCAN_RETENTION_DAYS: tuple[int, ...] = (30, 60, 90, 180, 365, KEEP_FOREVER)

SCREENSHOT_RETENTION_DAYS: tuple[int, ...] = (7, 14, 30, 60, 90, KEEP_FOREVER)

MAX_SCANS_PER_RUN = 200

KEEP_NEWEST_PER_TARGET = True

MEDIA_ROOT = Path("/app/scan_media")

# written by the toolbox
MEDIA_RESERVED = frozenset({"toolbox"})


def window_active(days: int) -> bool:
    return days > KEEP_FOREVER
