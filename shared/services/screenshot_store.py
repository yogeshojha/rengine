"""Bringing stored screenshots up to date: hashed, and held as WebP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import bindparam, or_, select, update
from sqlmodel import Session

from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.utils.imagehash import phash_image

logger = get_logger(__name__)

MEDIA_ROOT = "/app/scan_media"
SOURCE_SUFFIX = ".png"
STORED_SUFFIX = ".webp"
QUALITY = 80
# the encoder's effort setting: 2 holds most of the saving at a third of the cost
METHOD = 2
SCANS_PER_TICK = 2
_MODELS = (HttpAsset, Subdomain)


@dataclass(frozen=True)
class Rewritten:
    phash: int | None
    path: str | None


def absolute(stored: str) -> Path:
    path = Path(stored)
    return path if path.is_absolute() else Path(MEDIA_ROOT) / path


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(MEDIA_ROOT))
    except ValueError:
        return str(path)


def rewrite(stored: str) -> Rewritten:
    """Hash a render and, when it is still a PNG, replace it with a WebP."""
    from PIL import Image, UnidentifiedImageError  # noqa: PLC0415

    source = absolute(stored)
    try:
        if source.stat().st_size == 0:
            return Rewritten(None, None)
        with Image.open(source) as img:
            img.load()
            value = phash_image(img)
            if source.suffix.lower() != SOURCE_SUFFIX:
                return Rewritten(value, stored)
            target = source.with_suffix(STORED_SUFFIX)
            img.convert("RGB").save(target, "WEBP", quality=QUALITY, method=METHOD)
    except (OSError, UnidentifiedImageError, ValueError):
        return Rewritten(None, None)
    source.unlink(missing_ok=True)
    return Rewritten(value, relative(target))


def pending_scans(session: Session, *, limit: int) -> list[UUID]:
    """Settled scans still holding a PNG or an unhashed render."""
    found: list[UUID] = []
    for model in _MODELS:
        rows = session.execute(
            select(model.scan_id)
            .join(Scan, Scan.id == model.scan_id)
            .where(
                model.screenshot_path.isnot(None),
                Scan.status.in_(SCAN_TERMINAL_STATUSES),
                or_(
                    model.screenshot_phash.is_(None),
                    model.screenshot_path.endswith(SOURCE_SUFFIX),
                ),
            )
            .group_by(model.scan_id)
            .limit(limit)
        ).all()
        found.extend(row[0] for row in rows)
    return list(dict.fromkeys(found))[:limit]


def process_scan(session: Session, scan_id: UUID) -> tuple[int, int]:
    """Rewrite one scan's renders, returning the rows touched and bytes reclaimed."""
    stored = _paths_of(session, scan_id)
    if not stored:
        return 0, 0
    reclaimed = 0
    changes: list[dict] = []
    for path in stored:
        before = _size(path)
        done = rewrite(path)
        if done.path != path:
            reclaimed += max(0, before - _size(done.path))
        changes.append({"b_old": path, "b_phash": done.phash, "b_path": done.path})
    return _apply(session, changes), reclaimed


def _size(stored: str | None) -> int:
    if not stored:
        return 0
    try:
        return absolute(stored).stat().st_size
    except OSError:
        return 0


def _paths_of(session: Session, scan_id: UUID) -> list[str]:
    paths: set[str] = set()
    for model in _MODELS:
        rows = session.execute(
            select(model.screenshot_path)
            .where(
                model.scan_id == scan_id,
                model.screenshot_path.isnot(None),
                or_(
                    model.screenshot_phash.is_(None),
                    model.screenshot_path.endswith(SOURCE_SUFFIX),
                ),
            )
            .distinct()
        ).all()
        paths.update(row[0] for row in rows)
    return sorted(paths)


_UPDATES = {
    model: update(model)
    .where(model.screenshot_path == bindparam("b_old"))
    .values(
        screenshot_phash=bindparam("b_phash"),
        screenshot_path=bindparam("b_path"),
    )
    for model in _MODELS
}


def _apply(session: Session, changes: list[dict]) -> int:
    if not changes:
        return 0
    touched = 0
    for model in _MODELS:
        result = session.connection().execute(_UPDATES[model], changes)
        touched += result.rowcount or 0
    session.commit()
    return touched
