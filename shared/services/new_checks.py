"""Follow-up runs: a target's web assets tested with the checks the library gained."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import exists, func, not_, or_, select, text
from sqlalchemy.orm import Session

from shared.definitions.new_checks import (
    FOLLOW_UP_STAGES,
    MAX_SEEDS_PER_RUN,
    MAX_TEMPLATE_IDS,
    NEW_CHECKS_KEY,
    run_label,
)
from shared.definitions.notifications import NewChecksResult
from shared.definitions.rescan import ASSET_SEED_STAGE, SeedKind
from shared.definitions.scan_surface import DropReason, SurfaceClass
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, TemplateOrigin
from shared.enums.scan import SCAN_OPEN_STATUSES, ScanScope, ScanStatus
from shared.logging import get_logger
from shared.models.instance_settings import InstanceSettings
from shared.models.scan import Scan
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.target import Target
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage
from shared.services import locks
from shared.services.celery_dispatch import dispatch_scan_run
from shared.services.focused import focused_overrides
from shared.services.launch_plan import AdHocEngine
from shared.services.proxy_resolve import scan_proxy_url
from shared.services.scan_factory import build_scan_row
from shared.services.scan_resolve import merge_engine_context
from shared.services.scan_surface import split
from shared.services.vuln_templates import selected_templates
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_VULN_STAGE = FOLLOW_UP_STAGES[-1]

_COVERING_SCANS = """
SELECT DISTINCT ON (s.target_id) s.id
  FROM scans s
  JOIN targets t ON t.id = s.target_id
 WHERE t.new_checks
   AND s.status = :completed
   AND s.scope = :full
   AND NOT EXISTS (
       SELECT 1 FROM scans o
        WHERE o.target_id = s.target_id AND o.status = ANY(:open)
   )
 ORDER BY s.target_id, coalesce(s.started_at, s.created_at) DESC
"""

_WAITING_TARGETS = """
SELECT t.project_id, count(*)
  FROM targets t
 WHERE t.new_checks
   AND NOT EXISTS (
       SELECT 1 FROM scans s
        WHERE s.target_id = t.id AND s.status = :completed AND s.scope = :full
   )
   AND NOT EXISTS (
       SELECT 1 FROM scans o
        WHERE o.target_id = t.id AND o.status = ANY(:open)
   )
 GROUP BY t.project_id
"""

_BUSY_TARGETS = """
SELECT t.project_id, count(*)
  FROM targets t
 WHERE t.new_checks
   AND EXISTS (
       SELECT 1 FROM scans o
        WHERE o.target_id = t.id AND o.status = ANY(:open)
   )
 GROUP BY t.project_id
"""


@dataclass
class SweepResult:
    templates: int = 0
    started: Counter = field(default_factory=Counter)
    busy: Counter = field(default_factory=Counter)
    waiting: Counter = field(default_factory=Counter)
    skipped: Counter = field(default_factory=Counter)
    failed: int = 0
    scans: list[uuid.UUID] = field(default_factory=list)

    @property
    def targets(self) -> int:
        return sum(self.started.values())

    def projects(self) -> set[uuid.UUID]:
        return (
            set(self.started) | set(self.busy) | set(self.waiting) | set(self.skipped)
        )


# ---------- reads ----------


def new_templates(
    session: Session, since: datetime, until: datetime
) -> list[tuple[str, datetime]]:
    """Official checks the library gained in the window, oldest first, capped."""
    rows = session.execute(
        select(VulnTemplate.template_id, VulnTemplate.created_at)
        .where(
            VulnTemplate.origin == TemplateOrigin.OFFICIAL.value,
            VulnTemplate.enabled.is_(True),
            VulnTemplate.created_at > since,
            VulnTemplate.created_at <= until,
        )
        .order_by(VulnTemplate.created_at, VulnTemplate.template_id)
        .limit(MAX_TEMPLATE_IDS)
    )
    return [(str(template_id), created_at) for template_id, created_at in rows]


def window_end(rows: list[tuple[str, datetime]], until: datetime) -> datetime:
    """Where the next window starts."""
    if len(rows) >= MAX_TEMPLATE_IDS:
        return rows[-1][1]
    return until


def covering_scans(session: Session) -> list[Scan]:
    """The latest completed census run of every target that follows new checks."""
    ids = [
        row[0]
        for row in session.execute(
            text(_COVERING_SCANS),
            {
                "completed": ScanStatus.COMPLETED.value,
                "full": ScanScope.FULL.value,
                "open": list(SCAN_OPEN_STATUSES),
            },
        ).all()
    ]
    if not ids:
        return []
    scans = session.execute(select(Scan).where(Scan.id.in_(ids))).scalars().all()
    return sorted(scans, key=lambda s: str(s.target_id))


def waiting_targets(session: Session) -> Counter:
    """Following targets with no completed census run and no scan in flight."""
    rows = session.execute(
        text(_WAITING_TARGETS),
        {
            "completed": ScanStatus.COMPLETED.value,
            "full": ScanScope.FULL.value,
            "open": list(SCAN_OPEN_STATUSES),
        },
    )
    return Counter({project_id: int(n) for project_id, n in rows.all()})


def busy_targets(session: Session) -> Counter:
    rows = session.execute(text(_BUSY_TARGETS), {"open": list(SCAN_OPEN_STATUSES)})
    return Counter({project_id: int(n) for project_id, n in rows.all()})


def seeds_of(session: Session, target_id: uuid.UUID) -> list[dict]:
    """Every web asset the target's completed census runs planned, once each, newest first."""
    seen = func.max(func.coalesce(Scan.started_at, Scan.created_at))
    rows = session.execute(
        select(ScanSurfaceItem.value)
        .join(Scan, Scan.id == ScanSurfaceItem.scan_id)
        .where(
            Scan.target_id == target_id,
            Scan.status == ScanStatus.COMPLETED.value,
            Scan.scope == ScanScope.FULL.value,
            ScanSurfaceItem.class_ == SurfaceClass.ROOT.value,
            or_(
                ScanSurfaceItem.drop_reason.is_(None),
                ScanSurfaceItem.drop_reason == DropReason.COVERED_BY_ORIGIN.value,
            ),
        )
        .group_by(ScanSurfaceItem.value)
        .order_by(seen.desc(), ScanSurfaceItem.value)
        .limit(MAX_SEEDS_PER_RUN)
    )
    return [{"kind": SeedKind.URL.value, "value": str(v)} for (v,) in rows]


# ---------- build ----------


def build_run(
    session: Session,
    *,
    target: Target,
    covering: Scan,
    template_ids: list[str],
) -> Scan | None:
    """A focused run over the target's known web assets with the new checks only."""
    from stages.vulnerability_scan import config as vuln  # noqa: PLC0415

    engine = session.get(ScanEngine, covering.engine_id) if covering.engine_id else None
    if engine is not None and engine.project_id != target.project_id:
        engine = None
    context = (
        session.get(ScanContext, covering.context_id) if covering.context_id else None
    )
    if context is not None and context.project_id != target.project_id:
        context = None
    proxy_url = scan_proxy_url(session, context)

    overrides = focused_overrides(FOLLOW_UP_STAGES)
    overrides[_VULN_STAGE] = {
        **(overrides.get(_VULN_STAGE) or {}),
        "enabled": True,
        "template_ids": list(template_ids),
        "custom_templates": [],
    }
    resolved = merge_engine_context(
        engine or AdHocEngine(),
        context,
        target.target_value,
        target.target_type.value,
        proxy_url=proxy_url,
        overrides=overrides,
        intensity=(covering.execution_config or {}).get("intensity"),
    )
    # passive intensity switches the stage off after the override
    if not resolved.stage(_VULN_STAGE).get("enabled"):
        return None
    selection = vuln.VulnerabilityScanConfig(**resolved.stage(_VULN_STAGE)).selection()
    rows = selected_templates(session, selection)
    count = len(rows) - len(split(rows).unrunnable)
    if count <= 0:
        return None
    seeds = seeds_of(session, target.id)
    if not seeds:
        return None
    resolved.seed_assets = seeds
    resolved.seed_only = True
    resolved.stages[ASSET_SEED_STAGE] = {
        **(resolved.stages.get(ASSET_SEED_STAGE) or {}),
        "enabled": True,
    }
    label = run_label(count)
    scan = build_scan_row(
        resolved=resolved,
        engine=engine if engine is not None else AdHocEngine(name=label),
        context=context,
        target=target,
        project_id=target.project_id,
        created_by=covering.created_by,
        parent_scan_id=covering.id,
        dimension=SurfaceDimension.WEB_ASSETS.value,
    )
    scan.engine_name = label
    scan.execution_config = {**scan.execution_config, NEW_CHECKS_KEY: {"checks": count}}
    session.add(scan)
    session.flush()
    return scan


# ---------- sweep ----------


def sweep(session: Session) -> SweepResult:
    """One follow-up run per following target, for the checks it has not been tested with."""
    with locks.sync_lock(session, locks.NEW_CHECKS_SWEEP) as held:
        if not held:
            logger.info("new checks sweep already running")
            return SweepResult()
        return _sweep(session)


def _sweep(session: Session) -> SweepResult:
    settings = session.execute(select(InstanceSettings).limit(1)).scalars().first()
    result = SweepResult()
    if settings is None:
        return result
    now = utc_now()
    since = settings.new_checks_swept_at
    if since is None:
        settings.new_checks_swept_at = now
        session.commit()
        return result
    arrived = new_templates(session, since, now)
    result.templates = len(arrived)
    if arrived:
        result.busy = busy_targets(session)
        result.waiting = waiting_targets(session)
        windows: dict[datetime, list[tuple[str, datetime]]] = {since: arrived}
        for covering in covering_scans(session):
            target = session.get(Target, covering.target_id)
            if target is None:
                continue
            start = target.new_checks_swept_at or since
            rows = windows.get(start)
            if rows is None:
                rows = windows[start] = new_templates(session, start, now)
            _follow(
                session, result, target, covering, rows, start, window_end(rows, now)
            )
    settings.new_checks_swept_at = window_end(arrived, now)
    settings.updated_at = now
    session.commit()
    return result


def _follow(
    session: Session,
    result: SweepResult,
    target: Target,
    covering: Scan,
    rows: list[tuple[str, datetime]],
    start: datetime,
    end: datetime,
) -> None:
    """One target's follow-up. The watermark moves once the checks are handed over."""
    if not rows:
        target.new_checks_swept_at = end
        session.commit()
        return
    try:
        scan = build_run(
            session,
            target=target,
            covering=covering,
            template_ids=[template_id for template_id, _ in rows],
        )
    except Exception:
        session.rollback()
        result.failed += 1
        logger.warning(
            "new checks run not built", target=target.target_value, exc_info=True
        )
        return
    if scan is None:
        result.skipped[target.project_id] += 1
        target.new_checks_swept_at = end
        session.commit()
        return
    target.new_checks_swept_at = end
    session.commit()
    try:
        dispatch_scan_run(str(scan.id), scan.run_epoch)
    except Exception as exc:
        scan.status = ScanStatus.FAILED.value
        scan.error = "Not queued. Check that the worker is running."
        scan.completed_at = utc_now()
        target.new_checks_swept_at = start
        session.commit()
        result.failed += 1
        logger.warning("new checks run not queued", scan=str(scan.id), error=str(exc))
        return
    result.started[target.project_id] += 1
    result.scans.append(scan.id)


# ---------- result ----------


def is_follow_up(scan: Scan) -> bool:
    return bool((scan.execution_config or {}).get(NEW_CHECKS_KEY))


def _suppressed():
    return exists(
        select(1).where(
            VulnerabilityTriage.target_id == Vulnerability.target_id,
            VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
            VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
        )
    )


def result_of(session: Session, scan: Scan) -> NewChecksResult:
    """What a follow-up run found, by severity, suppressed findings left out."""
    rows = session.execute(
        select(Vulnerability.severity, func.count())
        .where(Vulnerability.scan_id == scan.id, not_(_suppressed()))
        .group_by(Vulnerability.severity)
    ).all()
    by_severity = {str(sev): int(n) for sev, n in rows}
    config = scan.execution_config or {}
    return NewChecksResult(
        scan_id=str(scan.id),
        target=str(config.get("target_value") or ""),
        checks=int((config.get(NEW_CHECKS_KEY) or {}).get("checks") or 0),
        findings=sum(by_severity.values()),
        by_severity=by_severity,
    )


__all__ = [
    "SweepResult",
    "build_run",
    "busy_targets",
    "covering_scans",
    "is_follow_up",
    "new_templates",
    "result_of",
    "seeds_of",
    "sweep",
    "waiting_targets",
    "window_end",
]
