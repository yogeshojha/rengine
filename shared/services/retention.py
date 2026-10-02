"""Apply the scan and evidence retention windows."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session, aliased

from shared.definitions.retention import (
    MAX_SCANS_PER_RUN,
    MEDIA_ROOT,
    window_active,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.activity_log import ActivityLog
from shared.models.endpoint import EndpointResponse
from shared.models.http_asset import HttpAsset
from shared.models.instance_settings import InstanceSettings
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.services.scan_scope import census_only
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


def _has_newer(*, census: bool):
    newer = aliased(Scan)
    conds = [
        newer.target_id == Scan.target_id,
        newer.created_at > Scan.created_at,
        newer.status.in_(SCAN_TERMINAL_STATUSES),
    ]
    if census:
        conds.append(census_only(newer))
    return exists(select(1).where(*conds))


def _protected():
    """The most recent terminal scan of every target, and its most recent census run."""
    return ~_has_newer(census=False) | (census_only() & ~_has_newer(census=True))


def _expired(days: int) -> tuple:
    cutoff = utc_now() - timedelta(days=days)
    return (
        Scan.status.in_(SCAN_TERMINAL_STATUSES),
        func.coalesce(Scan.completed_at, Scan.created_at) < cutoff,
    )


def _expired_scans(session: Session, days: int) -> list[UUID]:
    return list(
        session.execute(
            select(Scan.id)
            .where(*_expired(days), ~_protected())
            .order_by(func.coalesce(Scan.completed_at, Scan.created_at).asc())
            .limit(MAX_SCANS_PER_RUN + 1)
        ).scalars()
    )


def _kept_newest(session: Session, days: int) -> int:
    counted = session.scalar(
        select(func.count()).select_from(Scan).where(*_expired(days), _protected())
    )
    return int(counted or 0)


def _media_dir(scan_id: UUID) -> Path:
    return MEDIA_ROOT / str(scan_id)


def _drop_media(scan_id: UUID) -> int:
    """Remove a scan's screenshots and report the bytes reclaimed."""
    directory = _media_dir(scan_id)
    if not directory.is_dir():
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
    """Drop the stored bytes."""
    result = session.execute(
        update(HttpAsset)
        .where(HttpAsset.scan_id == scan_id, HttpAsset.response_body.isnot(None))
        .values(response_body=None)
    )
    responses = session.execute(
        delete(EndpointResponse).where(EndpointResponse.scan_id == scan_id)
    )
    return (result.rowcount or 0) + (responses.rowcount or 0)


@dataclass
class EvidencePrune:
    media_removed: int = 0
    media_bytes: int = 0
    bodies_removed: int = 0


def prune_evidence(session: Session, days: int) -> EvidencePrune:
    """Screenshots and response bodies, on their own retention window."""
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
    """Delete expired scans."""
    if not window_active(days):
        return ScanPrune()
    expired = _expired_scans(session, days)
    out = ScanPrune(
        kept_newest=_kept_newest(session, days),
        capped=len(expired) > MAX_SCANS_PER_RUN,
    )
    for scan_id in expired[:MAX_SCANS_PER_RUN]:
        _drop_media(scan_id)
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
