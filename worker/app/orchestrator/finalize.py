"""Aggregate stage outcomes into the final scan status + terminal notification/event."""

from sqlalchemy import Integer, String, bindparam, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from shared.config import BaseAppSettings
from shared.definitions.domain_posture import SPOOFABLE_KEYS
from shared.definitions.notifications import (
    SCAN_COUNT_COLUMNS,
    ScanDeltas,
    new_checks_result,
    scan_count_summary,
    scan_digest,
    scan_failed,
)
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.secrets import FINALIZE_SOURCES, SecretState
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, CoverageStatus
from shared.definitions.watch import WATCH_HOST_KEY
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.notification import NotificationType
from shared.enums.scan import (
    ACTIVITY_TERMINAL_STATUSES,
    SCAN_TERMINAL_STATUSES,
    ScanActivityStatus,
    ScanScope,
    ScanStatus,
)
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.vulnerability import VulnerabilityCoverage
from shared.services import (
    new_checks,
    proxy_sync,
    scan_admission,
    scan_deltas,
    scan_surface,
    secret_mining,
    software_match,
)
from shared.services.activity_log import ActivityLogService
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.celery_dispatch import (
    dispatch_interest_evaluation,
    dispatch_issue_observe,
    dispatch_threat_intel,
    dispatch_tripwire_settle,
    dispatch_watch_settle,
)
from shared.services.domain_posture import fold_onto_hosts
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.orchestrator import (
    aggregate_status,
    derived_counts,
)
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.planner_stats import analyze_result_tables
from shared.services.recheck import compute_rechecks
from shared.utils.datetime import utc_now
from stages.registry import ordered_levels

logger = get_logger(__name__)

_FINALIZE_SKIPPED = (
    ScanStatus.COMPLETED.value,
    ScanStatus.FAILED.value,
    ScanStatus.PAUSED.value,
)


def _undispatched(activities: list[ScanActivity]) -> str | None:
    """The stages the canvas did not reach."""
    expected = {spec.name for level in ordered_levels() for spec in level}
    covered = {a.name for a in activities if a.status in ACTIVITY_TERMINAL_STATUSES}
    if not expected - covered:
        return None
    return f"Stopped after {len(covered & expected)} of {len(expected)} stages."


def _notify(
    notifier: SyncNotificationPublisher,
    session: Session,
    scan: Scan,
    payload: dict | None,
) -> None:
    if payload is None:
        return
    try:
        notifier.publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=scan.project_id,
        )
    except Exception:
        logger.warning("scan notification dispatch failed", exc_info=True)


def _finalize_user_cancelled(
    session: Session, scan: Scan, events: ScanEventPublisher
) -> None:
    counts = _settled_counts(session, scan)
    locked = session.get(Scan, scan.id, with_for_update=True)
    if locked is None:
        session.commit()
        return
    first = locked.completed_at is None
    for column, value in counts.items():
        setattr(locked, column, value)
    if first:
        locked.completed_at = utc_now()
    session.add(locked)
    session.commit()
    scan = locked
    _admit_next(session)
    _settle(session, scan)
    if first:
        _log_cancelled(ActivityLogService(session), scan)
        session.commit()
    events.scan_cancelled(status=scan.status)


def _log_cancelled(activity_log: ActivityLogService, scan: Scan) -> None:
    target_value = (scan.execution_config or {}).get("target_value", "")
    activity_log.log(
        event=ActivityEvent.SCAN_CANCELLED,
        title=f"Scan cancelled · {target_value}",
        description=scan.engine_name,
        level=ActivityLevel.WARNING,
        project_id=scan.project_id,
        target_id=scan.target_id,
        scan_id=scan.id,
        target_value=target_value,
    )


_HOST_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM subdomains b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
"""

_SERVICE_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM ports b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
"""

_VULN_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM vulnerabilities b
    JOIN scans bs ON bs.id = b.scan_id
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
"""

_RUN_BASELINE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM scans bs
    WHERE bs.target_id = :tid AND bs.scope = 'full' AND bs.status = 'completed'
      AND bs.id <> :sid AND bs.started_at < :started
)
"""

_NEW_SUBDOMAINS_SQL = """
WITH seen AS (
    SELECT DISTINCT b.name FROM subdomains b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT count(*) AS total
FROM subdomains p
WHERE p.scan_id = :sid
  AND NOT EXISTS (SELECT 1 FROM seen s WHERE s.name = p.name)
"""

_NEW_SERVICES_SQL = """
WITH seen AS (
    SELECT DISTINCT b.ip, b.number FROM ports b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT count(*) AS total,
       count(*) FILTER (WHERE p.number = ANY(:sensitive_ports)) AS sensitive
FROM ports p
WHERE p.scan_id = :sid
  AND NOT EXISTS (
      SELECT 1 FROM seen s WHERE s.ip = p.ip AND s.number = p.number
  )
"""

_NEW_VULNS_SQL = """
WITH seen AS (
    SELECT DISTINCT b.fingerprint FROM vulnerabilities b
    JOIN scans bs ON bs.id = b.scan_id
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT v.severity AS severity,
       count(*) AS total,
       count(*) FILTER (WHERE v.is_kev) AS kev
FROM vulnerabilities v
WHERE v.scan_id = :sid
  AND NOT EXISTS (
      SELECT 1 FROM vulnerability_triage t
      WHERE t.target_id = v.target_id AND t.fingerprint = v.fingerprint
        AND t.state = ANY(:suppressed)
  )
  AND NOT EXISTS (SELECT 1 FROM seen s WHERE s.fingerprint = v.fingerprint)
GROUP BY v.severity
"""


_NEW_SECRETS_SQL = """
WITH seen AS (
    SELECT DISTINCT b.fingerprint FROM secrets b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
)
SELECT count(*) AS total
FROM secrets p
WHERE p.scan_id = :sid
  AND p.is_secret
  AND p.state = :exposed
  AND NOT EXISTS (SELECT 1 FROM seen s WHERE s.fingerprint = p.fingerprint)
"""


_POSTURE_REGRESSIONS_SQL = """
WITH prev AS (
    SELECT DISTINCT ON (b.zone) b.zone, b.posture_issues
    FROM domain_posture b
    JOIN scans bs ON bs.id = b.scan_id AND bs.scope = 'full'
                 AND bs.id <> :sid AND bs.started_at < :started
    WHERE b.target_id = :tid
    ORDER BY b.zone, bs.started_at DESC
)
SELECT count(*) AS total
FROM domain_posture p
JOIN prev ON prev.zone = p.zone
WHERE p.scan_id = :sid
  AND EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(p.posture_issues::jsonb) k
      WHERE k.value = ANY(:keys)
        AND NOT (prev.posture_issues::jsonb ? k.value)
  )
"""


def _has_baseline(session: Session, scan: Scan, sql: str) -> bool:
    return bool(session.execute(text(sql).bindparams(*_scope(scan))).scalar_one())


def _scope(scan: Scan) -> list:
    return [
        bindparam("sid", scan.id),
        bindparam("tid", scan.target_id),
        bindparam("started", scan.started_at or utc_now()),
    ]


def _count_new_subdomains(session: Session, scan: Scan) -> int:
    return int(
        session.execute(
            text(_NEW_SUBDOMAINS_SQL).bindparams(*_scope(scan))
        ).scalar_one()
        or 0
    )


def _count_new_services(session: Session, scan: Scan) -> tuple[int, int]:
    row = session.execute(
        text(_NEW_SERVICES_SQL).bindparams(
            *_scope(scan),
            bindparam("sensitive_ports", SENSITIVE_PORTS, type_=ARRAY(Integer)),
        )
    ).one()
    return int(row.total or 0), int(row.sensitive or 0)


def _count_new_vulnerabilities(session: Session, scan: Scan) -> tuple[dict, int, int]:
    rows = session.execute(
        text(_NEW_VULNS_SQL).bindparams(
            *_scope(scan),
            bindparam("suppressed", list(SUPPRESSED_STATES), type_=ARRAY(String)),
        )
    ).all()
    counts = {row.severity: int(row.total) for row in rows}
    kev = sum(int(row.kev or 0) for row in rows)
    return counts, kev, sum(counts.values())


def _count_new_secrets(session: Session, scan: Scan) -> int:
    return int(
        session.execute(
            text(_NEW_SECRETS_SQL).bindparams(
                *_scope(scan), bindparam("exposed", SecretState.EXPOSED.value)
            )
        ).scalar_one()
        or 0
    )


def _posture_regressions(session: Session, scan: Scan) -> int:
    return int(
        session.execute(
            text(_POSTURE_REGRESSIONS_SQL).bindparams(
                *_scope(scan),
                bindparam("keys", list(SPOOFABLE_KEYS), type_=ARRAY(String)),
            )
        ).scalar_one()
        or 0
    )


def _dropped_hosts(session: Session, scan: Scan) -> int:
    rows = (
        session.execute(
            select(VulnerabilityCoverage.hosts_dropped).where(
                VulnerabilityCoverage.scan_id == scan.id,
                VulnerabilityCoverage.status == CoverageStatus.PARTIAL.value,
            )
        )
        .scalars()
        .all()
    )
    return len({drop.get("host") for entry in rows for drop in entry or []})


def _dispatch_interest(session: Session, scan: Scan) -> None:
    try:
        dispatch_interest_evaluation(str(scan.id), digest=True)
    except Exception:
        logger.warning("interest dispatch failed", exc_info=True)
        notify_digest(session, scan)


def notify_digest(session: Session, scan: Scan, exposures: int = 0) -> None:
    counts = {col: getattr(scan, col, 0) or 0 for col in SCAN_COUNT_COLUMNS}
    target_value = (scan.execution_config or {}).get("target_value", "")
    _notify(
        SyncNotificationPublisher(BaseAppSettings().redis_url),
        session,
        scan,
        scan_digest(
            str(scan.id), target_value, counts, _measure(session, scan, exposures)
        ),
    )


def _dispatch_intel(scan: Scan) -> None:
    dispatch_threat_intel(str(scan.id))


def _match_software(session: Session, scan: Scan) -> None:
    software_match.match_scan(
        session,
        scan_id=scan.id,
        target_id=scan.target_id,
        project_id=scan.project_id,
    )


def _guard(session: Session, fn, fallback):
    try:
        return fn()
    except Exception:
        session.rollback()
        logger.warning("finalize step failed", exc_info=True)
        return fallback


def _refold_posture(session: Session, scan: Scan) -> None:
    fold_onto_hosts(session, scan.id)
    session.commit()


def _mine_findings(session: Session, scan: Scan) -> None:
    """Read the finding responses the scanners wrote after the stage ran."""
    if not secret_mining.stage_mined(session, scan.id):
        return
    outcome = secret_mining.mine_scan(
        session,
        scan_id=scan.id,
        target_id=scan.target_id,
        project_id=scan.project_id,
        sources=FINALIZE_SOURCES,
        incremental=True,
    )
    if outcome.busy:
        logger.warning(
            "finding responses not mined, scan is locked", scan_id=str(scan.id)
        )


def _settled_counts(session: Session, scan: Scan) -> dict:
    _guard(session, lambda: _match_software(session, scan), None)
    _guard(session, lambda: _mine_findings(session, scan), None)
    _guard(session, lambda: _refold_posture(session, scan), None)
    _guard(session, lambda: analyze_result_tables(session), None)
    return derived_counts(session, scan.id)


def _measure(session: Session, scan: Scan, exposures: int = 0) -> ScanDeltas:
    """Deltas are measured against every earlier run, a clean earlier run included."""
    hosts, services, vulns, run = (
        _guard(session, lambda sql=sql: _has_baseline(session, scan, sql), False)
        for sql in (
            _HOST_BASELINE_SQL,
            _SERVICE_BASELINE_SQL,
            _VULN_BASELINE_SQL,
            _RUN_BASELINE_SQL,
        )
    )
    new_services, sensitive = _guard(
        session, lambda: _count_new_services(session, scan), (0, 0)
    )
    vuln_counts, kev, new_vulns = _guard(
        session, lambda: _count_new_vulnerabilities(session, scan), ({}, 0, 0)
    )
    return ScanDeltas(
        baseline=hosts or services or vulns or run,
        new_hosts=_guard(session, lambda: _count_new_subdomains(session, scan), 0),
        new_services=new_services,
        sensitive_services=sensitive,
        new_vulnerabilities=new_vulns,
        vulnerability_counts=vuln_counts,
        kev=kev,
        new_secrets=_guard(session, lambda: _count_new_secrets(session, scan), 0),
        exposures=exposures,
        dropped_hosts=_guard(session, lambda: _dropped_hosts(session, scan), 0),
        posture_regressions=_guard(
            session, lambda: _posture_regressions(session, scan), 0
        ),
    )


def _settle(session: Session, scan: Scan) -> None:
    """Settle the per-scope work a terminal run leaves behind."""
    if scan.scope == ScanScope.FOCUSED.value and not new_checks.is_follow_up(scan):
        try:
            compute_rechecks(session, scan)
        except Exception:
            logger.warning("recheck diff failed for scan %s", scan.id, exc_info=True)
    try:
        proxy_sync.replay(session, scan)
        proxy_sync.settle_queue(session, scan)
    except Exception:
        session.rollback()
        logger.warning("proxy sync failed for scan %s", scan.id, exc_info=True)
    try:
        scan_surface.settle(session, scan.id)
    except Exception:
        session.rollback()
        logger.warning("surface settle failed for scan %s", scan.id, exc_info=True)
    try:
        scan_deltas.warm(session, scan)
    except Exception:
        session.rollback()
        logger.warning("scan deltas failed for scan %s", scan.id, exc_info=True)
    bump_sync([scan.target_id])
    if (scan.execution_config or {}).get(WATCH_HOST_KEY):
        dispatch_watch_settle(str(scan.id))
    dispatch_tripwire_settle(str(scan.id))


def _admit_next(session: Session) -> None:
    try:
        scan_admission.admit_waiting(session)
    except Exception:
        session.rollback()
        logger.warning("queued scans not started", exc_info=True)


def finalize_scan_run(session: Session, scan: Scan, *, redis_url: str) -> None:
    events = ScanEventPublisher(
        redis_url, scan_id=str(scan.id), project_id=str(scan.project_id)
    )
    notifier = SyncNotificationPublisher(redis_url)
    target_value = (scan.execution_config or {}).get("target_value", "")

    if scan.status in _FINALIZE_SKIPPED:
        return

    if scan.status == ScanStatus.CANCELLED.value:
        _finalize_user_cancelled(session, scan, events)
        return

    activities = (
        session.execute(select(ScanActivity).where(ScanActivity.scan_id == scan.id))
        .scalars()
        .all()
    )
    status = aggregate_status(activities)
    if status == ScanStatus.RUNNING.value:
        logger.info("finalize deferred: scan %s still has in-flight stages", scan.id)
        return
    truncated = (
        _undispatched(list(activities))
        if status == ScanStatus.COMPLETED.value
        else None
    )
    if truncated:
        status = ScanStatus.FAILED.value
        logger.error("scan %s finalized incomplete: %s", scan.id, truncated)
    counts = _settled_counts(session, scan)

    locked = session.get(Scan, scan.id, with_for_update=True)
    if locked is None or locked.status in SCAN_TERMINAL_STATUSES:
        session.commit()
        return

    for column, value in counts.items():
        setattr(locked, column, value)
    locked.status = status
    locked.completed_at = utc_now()
    duration = (
        (locked.completed_at - locked.started_at).total_seconds()
        - (locked.paused_seconds or 0.0)
        if locked.started_at
        else None
    )

    if status == ScanStatus.FAILED.value:
        failed = next(
            (
                a
                for a in activities
                if a.status == ScanActivityStatus.FAILED.value and a.error
            ),
            None,
        )
        locked.error = (
            truncated
            or (
                failed.error if failed and failed.error else "One or more stages failed"
            )
        )[:2000]
    session.add(locked)
    session.commit()
    scan = locked
    _admit_next(session)
    _settle(session, scan)

    activity_log = ActivityLogService(session)

    if status == ScanStatus.CANCELLED.value:
        _log_cancelled(activity_log, scan)
        session.commit()
        events.scan_cancelled(status=status)
        return

    if status == ScanStatus.COMPLETED.value:
        activity_log.log(
            event=ActivityEvent.SCAN_COMPLETED,
            title=f"Scan completed · {target_value}",
            description=scan_count_summary(counts),
            level=ActivityLevel.SUCCESS,
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            target_value=target_value,
        )
        session.commit()
        events.scan_completed(status=status, counts=counts, duration_seconds=duration)
        _dispatch_intel(scan)
        if new_checks.is_follow_up(scan):
            _notify(
                notifier,
                session,
                scan,
                new_checks_result(new_checks.result_of(session, scan)),
            )
        if scan.scope != ScanScope.FOCUSED.value:
            dispatch_issue_observe(str(scan.id))
            _dispatch_interest(session, scan)
        return

    activity_log.log(
        event=ActivityEvent.SCAN_FAILED,
        title=f"Scan failed · {target_value}",
        description=scan.error or "One or more stages failed",
        level=ActivityLevel.ERROR,
        project_id=scan.project_id,
        target_id=scan.target_id,
        scan_id=scan.id,
        target_value=target_value,
    )
    session.commit()
    events.scan_failed(status=status, error=scan.error)
    _notify(
        notifier,
        session,
        scan,
        scan_failed(
            str(scan.id),
            target_value,
            scan.engine_name,
            scan.error or "unknown error",
            ntype=NotificationType.NEW_CHECKS
            if new_checks.is_follow_up(scan)
            else NotificationType.SCAN,
        ),
    )
