"""Enforce the retention windows the settings page promises."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from shared.definitions.retention import (
    KEEP_NEWEST_PER_TARGET,
    MAX_SCANS_PER_RUN,
    MEDIA_RESERVED,
    MEDIA_ROOT,
    window_active,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.activity_log import ActivityLog
from shared.models.http_asset import HttpAsset
from shared.models.instance_settings import InstanceSettings
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass
class RetentionResult:
    scans_removed: int = 0
    activity_removed: int = 0
    media_removed: int = 0
    media_bytes: int = 0
    bodies_removed: int = 0
    scans_kept_newest: int = 0
    capped: bool = False
    windows: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "scans_removed": self.scans_removed,
            "activity_removed": self.activity_removed,
            "media_removed": self.media_removed,
            "media_bytes": self.media_bytes,
            "bodies_removed": self.bodies_removed,
            "scans_kept_newest": self.scans_kept_newest,
            "capped": self.capped,
            **self.windows,
        }


def _settings(session: Session) -> InstanceSettings | None:
    return session.execute(select(InstanceSettings).limit(1)).scalars().first()


def _newest_per_target(session: Session) -> set[UUID]:
    """The most recent terminal scan of every target, which retention never removes."""
    newest = (
        select(Scan.target_id, func.max(Scan.created_at).label("at"))
        .where(Scan.status.in_(SCAN_TERMINAL_STATUSES))
        .group_by(Scan.target_id)
        .subquery()
    )
    rows = session.execute(
        select(Scan.id)
        .join(
            newest,
            (Scan.target_id == newest.c.target_id) & (Scan.created_at == newest.c.at),
        )
        .where(Scan.status.in_(SCAN_TERMINAL_STATUSES))
    ).scalars()
    return set(rows)


def _expired_scans(session: Session, days: int) -> list[UUID]:
    cutoff = utc_now() - timedelta(days=days)
    return list(
        session.execute(
            select(Scan.id)
            .where(
                Scan.status.in_(SCAN_TERMINAL_STATUSES),
                func.coalesce(Scan.completed_at, Scan.created_at) < cutoff,
            )
            .order_by(func.coalesce(Scan.completed_at, Scan.created_at).asc())
            .limit(MAX_SCANS_PER_RUN + 1)
        ).scalars()
    )


def _media_dir(scan_id: UUID) -> Path:
    return MEDIA_ROOT / str(scan_id)


def _drop_media(scan_id: UUID) -> int:
    """Remove a scan's screenshots and report the bytes reclaimed."""
    directory = _media_dir(scan_id)
    if directory.name in MEDIA_RESERVED or not directory.is_dir():
        return 0
    size = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    shutil.rmtree(directory, ignore_errors=True)
    return size


def _forget_media(session: Session, scan_id: UUID) -> None:
    for model in (Subdomain, HttpAsset):
        session.execute(
            update(model)
            .where(model.scan_id == scan_id, model.screenshot_path.isnot(None))
            .values(screenshot_path=None)
        )


def _forget_bodies(session: Session, scan_id: UUID) -> int:
    """The bytes go; content_hash, favicon_hash and the rest of the identity stay,
    so correlation still works on a scan whose evidence has aged out."""
    result = session.execute(
        update(HttpAsset)
        .where(HttpAsset.scan_id == scan_id, HttpAsset.response_body.isnot(None))
        .values(response_body=None)
    )
    return result.rowcount or 0


@dataclass
class EvidencePrune:
    media_removed: int = 0
    media_bytes: int = 0
    bodies_removed: int = 0


def prune_evidence(session: Session, days: int) -> EvidencePrune:
    """Screenshots and response bodies are the bulk of a scan and age out first,
    on their own window, well before the findings they were evidence for."""
    out = EvidencePrune()
    if not window_active(days):
        return out
    cutoff = utc_now() - timedelta(days=days)
    scans = session.execute(
        select(Scan.id).where(
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
            func.coalesce(Scan.completed_at, Scan.created_at) < cutoff,
        )
    ).scalars()
    for scan_id in scans:
        had_media = _media_dir(scan_id).is_dir()
        if had_media:
            out.media_bytes += _drop_media(scan_id)
            _forget_media(session, scan_id)
            out.media_removed += 1
        bodies = _forget_bodies(session, scan_id)
        out.bodies_removed += bodies
        if had_media or bodies:
            session.commit()
    return out


@dataclass
class ScanPrune:
    removed: int = 0
    kept_newest: int = 0
    activity_removed: int = 0
    capped: bool = False


def prune_scans(session: Session, days: int) -> ScanPrune:
    """Older runs go with everything cascading off them; a target keeps its newest."""
    if not window_active(days):
        return ScanPrune()
    expired = _expired_scans(session, days)
    out = ScanPrune(capped=len(expired) > MAX_SCANS_PER_RUN)
    expired = expired[:MAX_SCANS_PER_RUN]
    if not expired:
        return out

    protected = _newest_per_target(session) if KEEP_NEWEST_PER_TARGET else set()
    for scan_id in expired:
        if scan_id in protected:
            out.kept_newest += 1
            continue
        _drop_media(scan_id)
        # activity_logs.scan_id carries no FK, so the run trail must be removed by hand
        trail = session.execute(
            ActivityLog.__table__.delete().where(ActivityLog.scan_id == scan_id)
        )
        session.execute(Scan.__table__.delete().where(Scan.id == scan_id))
        session.commit()
        out.activity_removed += trail.rowcount or 0
        out.removed += 1
    return out


def enforce(session: Session) -> RetentionResult:
    settings = _settings(session)
    if settings is None:
        return RetentionResult()

    scan_days = settings.scan_history_retention_days
    shot_days = settings.screenshot_retention_days
    result = RetentionResult(
        windows={"scan_days": scan_days, "screenshot_days": shot_days}
    )

    evidence = prune_evidence(session, shot_days)
    result.media_removed = evidence.media_removed
    result.media_bytes = evidence.media_bytes
    result.bodies_removed = evidence.bodies_removed
    pruned = prune_scans(session, scan_days)
    result.scans_removed = pruned.removed
    result.scans_kept_newest = pruned.kept_newest
    result.activity_removed = pruned.activity_removed
    result.capped = pruned.capped

    if result.scans_removed or result.media_removed or result.bodies_removed:
        logger.info(
            "retention enforced",
            scans_removed=result.scans_removed,
            media_removed=result.media_removed,
            media_bytes=result.media_bytes,
            bodies_removed=result.bodies_removed,
            kept_newest=result.scans_kept_newest,
            capped=result.capped,
        )
    return result
