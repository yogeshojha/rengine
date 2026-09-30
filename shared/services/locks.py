"""Advisory locks for instance-wide work that must not run twice at once."""

from __future__ import annotations

import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# bounty_platform() spans BOUNTY_SYNC .. BOUNTY_SYNC + 0xFFFF
BOUNTY_SYNC = 0x624F0001
# bounty_reports() spans BOUNTY_REPORTS .. BOUNTY_REPORTS + 0xFFFF
BOUNTY_REPORTS = 0x62520001
# dataset() spans DATASET_SYNC .. DATASET_SYNC + 0xFFFF
DATASET_SYNC = 0x44530001
# secret_mining() spans SECRET_MINING .. SECRET_MINING + 0xFFFF
SECRET_MINING = 0x53450001
SOFTWARE_BACKFILL = 0x53570001
# software_match() spans SOFTWARE_MATCH .. SOFTWARE_MATCH + 0xFFFF
SOFTWARE_MATCH = 0x53580001
NEW_CHECKS_SWEEP = 0x4E430001
SCAN_ADMISSION = 0x53410001
SCAN_DELTAS_BACKFILL = 0x53440001
ISSUE_FILING = 0x49460001
# issue_observe() spans ISSUE_OBSERVE .. ISSUE_OBSERVE + 0xFFFF
ISSUE_OBSERVE = 0x494F0001
# issue_tracker() spans ISSUE_TRACKER .. ISSUE_TRACKER + 0xFFFF
ISSUE_TRACKER = 0x49540001


def bounty_platform(platform: str) -> int:
    """One lock per platform."""
    return BOUNTY_SYNC + (zlib.crc32(platform.encode()) & 0xFFFF)


def dataset(kind: str) -> int:
    """One lock per downloaded dataset, held while it loads."""
    return DATASET_SYNC + (zlib.crc32(kind.encode()) & 0xFFFF)


def bounty_reports(platform: str) -> int:
    """One lock per platform."""
    return BOUNTY_REPORTS + (zlib.crc32(platform.encode()) & 0xFFFF)


def secret_mining(scan_id: object) -> int:
    """One lock per scan: the stage, the backfill and a re-mine never overlap."""
    return SECRET_MINING + (zlib.crc32(str(scan_id).encode()) & 0xFFFF)


def software_match(scan_id: object) -> int:
    """One lock per scan."""
    return SOFTWARE_MATCH + (zlib.crc32(str(scan_id).encode()) & 0xFFFF)


def issue_tracker(tracker_id: object) -> int:
    """One lock per tracker: writes to one tracker run one at a time."""
    return ISSUE_TRACKER + (zlib.crc32(str(tracker_id).encode()) & 0xFFFF)


def issue_observe(target_id: object) -> int:
    """One lock per target."""
    return ISSUE_OBSERVE + (zlib.crc32(str(target_id).encode()) & 0xFFFF)


@contextmanager
def sync_lock(session: Session, key: int) -> Iterator[bool]:
    """Session-level advisory lock. Yields False when another session holds it."""
    held = bool(
        session.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
        ).scalar_one()
    )
    try:
        yield held
    finally:
        if held:
            session.rollback()
            session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
            session.commit()
