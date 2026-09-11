from __future__ import annotations

from pathlib import Path

KEEP_FOREVER = 0

MAX_SCANS_PER_RUN = 200

KEEP_NEWEST_PER_TARGET = True

MEDIA_ROOT = Path("/app/scan_media")

# written by the toolbox, which prunes its own runs
MEDIA_RESERVED = frozenset({"toolbox"})


def window_active(days: int) -> bool:
    return days > KEEP_FOREVER
