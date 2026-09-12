"""Advisory locks for instance-wide work that must not run twice at once."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

IP_RANGES = 0x624E0001


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
