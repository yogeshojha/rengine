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
BOUNTY_FEED = 0x624F0002
IP_RANGES = 0x624E0001


def bounty_platform(platform: str) -> int:
    """One lock per platform."""
    return BOUNTY_SYNC + (zlib.crc32(platform.encode()) & 0xFFFF)


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
