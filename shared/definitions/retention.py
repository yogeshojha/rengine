from __future__ import annotations

from pathlib import Path

# a window of 0 keeps everything: retention is opt-out, and 0 is how an operator opts out
KEEP_FOREVER = 0

# one run never deletes more than this, so a first pass over a long backlog cannot
# hold the database for an operator who has just turned retention on
MAX_SCANS_PER_RUN = 200

# a target's newest run is kept whatever its age: "Not scanned" must mean never
# scanned, never "scanned and then pruned"
KEEP_NEWEST_PER_TARGET = True

MEDIA_ROOT = Path("/app/scan_media")

# written by the toolbox, which prunes its own runs
MEDIA_RESERVED = frozenset({"toolbox"})


def window_active(days: int) -> bool:
    return days > KEEP_FOREVER
