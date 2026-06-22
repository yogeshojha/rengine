"""Celery task that executes a resolved scan: runs the enabled engines for a target."""

import uuid

from celery import shared_task
from sqlalchemy import delete, select

from app.database import get_sync_session
from engines.base import EngineContext
from engines.subdomain.engine import SubdomainEngine
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import ScanStatus
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.services.activity_log import ActivityLogService
from shared.services.scan_resolve import ResolvedScanConfig
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

ENGINES = (SubdomainEngine,)
_TERMINAL_STATUSES = (ScanStatus.COMPLETED.value, ScanStatus.CANCELLED.value)


@shared_task(
    bind=True,
    name="app.tasks.scan.run_scan",
    max_retries=0,
    soft_time_limit=3000,
    time_limit=3600,
)
def run_scan(self, scan_id: str) -> dict:  # noqa: ARG001
    """Run all enabled engines for a pending scan and persist results."""
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            logger.warning("scan %s not found", scan_id)
            return {"error": "scan not found"}
        # reclaim non-terminal scans on redelivery; engine persist is idempotent per scan_id
        if scan.status in _TERMINAL_STATUSES:
            logger.info("scan %s already %s, skipping", scan_id, scan.status)
            return {"skipped": scan.status}

        activity = ActivityLogService(session)
        scan.status = ScanStatus.RUNNING.value
        scan.started_at = utc_now()
        scan.error = None
        session.commit()

        try:
            activity.log(
                event=ActivityEvent.SCAN_STARTED,
                title="Scan started",
                description=f"{scan.engine_name}",
                level=ActivityLevel.INFO,
                project_id=scan.project_id,
                target_id=scan.target_id,
            )
            session.commit()

            resolved = _load_config(scan.execution_config)
            context = EngineContext(
                scan_id=scan.id,
                target_id=scan.target_id,
                project_id=scan.project_id,
                target_value=resolved.target_value,
                target_type=resolved.target_type,
                resolved=resolved,
            )
            counts = _run_engines(session, context)

            current = session.execute(
                select(Scan.status).where(Scan.id == scan.id)
            ).scalar_one_or_none()
            if current != ScanStatus.RUNNING.value:
                logger.info(
                    "scan %s no longer running (%s); preserving status",
                    scan_id,
                    current,
                )
                return {"status": current or "deleted", **counts}

            scan.subdomains_found = counts.get("subdomains", 0)
            scan.ips_found = counts.get("ips", 0)
            scan.status = ScanStatus.COMPLETED.value
            scan.completed_at = utc_now()
            session.commit()

            activity.log(
                event=ActivityEvent.SCAN_COMPLETED,
                title="Scan completed",
                description=(
                    f"{counts.get('subdomains', 0)} subdomains "
                    f"({counts.get('active', 0)} active)"
                ),
                level=ActivityLevel.SUCCESS,
                project_id=scan.project_id,
                target_id=scan.target_id,
            )
            session.commit()
            return {"status": "completed", **counts}

        except Exception as e:
            logger.error("scan %s failed: %s", scan_id, e, exc_info=True)
            session.rollback()
            _mark_failed(session, uuid.UUID(scan_id), str(e))
            return {"status": "failed", "error": str(e)[:300]}


def _load_config(execution_config: dict) -> ResolvedScanConfig:
    clean = {k: v for k, v in (execution_config or {}).items() if not k.startswith("_")}
    return ResolvedScanConfig(**clean)


def _run_engines(session, context: EngineContext) -> dict[str, int]:
    counts: dict[str, int] = {}
    for engine_cls in ENGINES:
        engine = engine_cls(session, context)
        if not engine.should_run():
            logger.info(
                "engine %s skipped for scan %s", engine_cls.name, context.scan_id
            )
            continue
        result = engine.run()
        for key, value in result.counts.items():
            counts[key] = counts.get(key, 0) + value
    return counts


def _mark_failed(session, scan_id: uuid.UUID, error: str) -> None:
    scan = session.get(Scan, scan_id)
    if scan is None:
        return
    if scan.status == ScanStatus.CANCELLED.value:
        return
    session.execute(delete(Subdomain).where(Subdomain.scan_id == scan_id))
    scan.status = ScanStatus.FAILED.value
    scan.error = error[:2000]
    scan.subdomains_found = 0
    scan.ips_found = 0
    scan.completed_at = utc_now()
    session.commit()
    ActivityLogService(session).log(
        event=ActivityEvent.SCAN_FAILED,
        title="Scan failed",
        description=error[:1000],
        level=ActivityLevel.ERROR,
        project_id=scan.project_id,
        target_id=scan.target_id,
    )
    session.commit()
