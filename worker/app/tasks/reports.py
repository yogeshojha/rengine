"""Report generation."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from celery import shared_task
from sqlalchemy import func

from app.database import get_sync_session
from reports import theme_store
from reports.pipeline import generate
from shared.definitions.reports import (
    FORMAT_EXTENSIONS,
    GENERATING_STATUSES,
    REPORT_ROOT,
    RETENTION_DAYS,
    STRANDED_ERROR,
    ReportSpec,
    ReportStatus,
    stranded_after,
)
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.logging import get_logger
from shared.models.report import Report
from shared.models.scan import Scan
from shared.models.target import Target
from shared.services.ai import ledger
from shared.services.notification_sync import SyncNotificationPublisher
from shared.utils.datetime import utc_now
from shared.utils.files import purge_dir
from shared.utils.slug import generate_slug

logger = get_logger(__name__)


def _root(report_id: UUID) -> Path:
    path = Path(REPORT_ROOT) / str(report_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


@shared_task(bind=True, name="app.tasks.reports.generate", max_retries=0)
def generate_report(self, report_id: str) -> dict:
    started = time.monotonic()

    with get_sync_session() as session:
        report = session.get(Report, UUID(report_id))
        if report is None:
            logger.warning("report missing", report_id=report_id)
            return {"status": "missing"}

        report.status = ReportStatus.RUNNING.value
        report.started_at = utc_now()
        report.task_id = self.request.id
        report.progress = 5
        report.step = "Starting"
        report.error = None
        session.add(report)
        session.commit()

        def progress(percent: int, label: str) -> None:
            report.progress = percent
            report.step = label
            session.add(report)
            session.commit()

        try:
            spec = ReportSpec.model_validate(report.spec or {})
            scan, target = _subject(session, report)
            theme_store.sync_builtin(session)
            with ledger.source("report", report.id):
                output = generate(
                    session,
                    spec,
                    scan=scan,
                    target=target,
                    progress=progress,
                )

            stem = (
                generate_slug(f"{spec.title or 'report'}-{target.target_value}")[:80]
                or "report"
            )
            files = _write_files(report, output, stem)

            _finish(report, output, files, round(time.monotonic() - started, 2))
            session.add(report)
            session.commit()
            logger.info(
                "report ready",
                report_id=report_id,
                pages=output.pages,
                seconds=report.duration_seconds,
            )
            return {"status": report.status, "pages": output.pages, "files": len(files)}

        except Exception as exc:
            _fail(session, report_id, exc, round(time.monotonic() - started, 2))
            logger.exception("report failed", report_id=report_id)
            raise


def _fail(session, report_id: str, exc: Exception, seconds: float) -> None:
    session.rollback()
    report = session.get(Report, UUID(report_id))
    if report is None:
        return
    report.status = ReportStatus.FAILED.value
    report.error = str(exc)[:2000]
    report.step = "Failed"
    report.completed_at = utc_now()
    report.duration_seconds = seconds
    session.add(report)
    session.commit()
    _notify_failed(session, report)


def _subject(session, report: Report) -> tuple[Scan | None, Target]:
    target = session.get(Target, report.target_id) if report.target_id else None
    scan = session.get(Scan, report.scan_id) if report.scan_id else None
    if target is None and scan is not None:
        target = session.get(Target, scan.target_id)
    if target is None:
        msg = "The report has no target."
        raise ValueError(msg)
    return scan, target


def _write_files(report: Report, output, stem: str) -> list[dict]:
    root = _root(report.id)
    files: list[dict] = []
    for fmt, data in output.files.items():
        name = f"{stem}.{FORMAT_EXTENSIONS.get(fmt, fmt)}"
        (root / name).write_bytes(data)
        files.append(
            {
                "format": fmt,
                "filename": name,
                "bytes": len(data),
                "pages": output.pages if fmt == "pdf" else None,
            }
        )
    return files


def _finish(report: Report, output, files: list[dict], seconds: float) -> None:
    report.files = files
    report.page_count = output.pages
    report.stats = output.stats
    report.ai_used = output.ai_used
    report.ai_provider = output.ai_provider or None
    report.ai_model = output.ai_model or None
    report.ai_calls = output.usage.calls
    report.ai_cached_calls = output.usage.cached
    report.ai_input_tokens = output.usage.input_tokens
    report.ai_output_tokens = output.usage.output_tokens
    report.status = ReportStatus.COMPLETED.value
    report.progress = 100
    report.step = "Ready"
    report.completed_at = utc_now()
    report.duration_seconds = seconds
    report.expires_at = utc_now() + timedelta(days=RETENTION_DAYS)


def _notify_failed(session, report: Report) -> None:
    name = report.title or report.template_name or "Report"
    try:
        SyncNotificationPublisher().publish(
            session,
            NotificationType.SYSTEM,
            NotificationSeverity.ERROR,
            "Report failed",
            f"{name} · {report.subject}. Check the worker log.",
            metadata={"url": "/reports"},
            project_id=report.project_id,
        )
    except Exception:
        logger.debug("report notification skipped", exc_info=True)


@shared_task(name="app.tasks.reports.cleanup")
def cleanup() -> dict:
    """An expired report keeps its recipe and loses its files."""
    removed = 0
    with get_sync_session() as session:
        now = utc_now()
        rows = (
            session.query(Report)
            .filter(
                Report.status == ReportStatus.COMPLETED.value,
                Report.expires_at.is_not(None),
                Report.expires_at < now,
            )
            .limit(500)
            .all()
        )
        for report in rows:
            purge_dir(REPORT_ROOT, report.id)
            report.files = []
            report.status = ReportStatus.EXPIRED.value
            report.step = "Expired"
            session.add(report)
            removed += 1
        if removed:
            session.commit()
    return {"removed": removed}


@shared_task(name="app.tasks.reports.reap")
def reap() -> int:
    """Fail reports that stopped without finishing."""
    cutoff = utc_now() - stranded_after()
    with get_sync_session() as session:
        rows = (
            session.query(Report)
            .filter(
                Report.status.in_(GENERATING_STATUSES),
                func.coalesce(Report.started_at, Report.created_at) <= cutoff,
            )
            .all()
        )
        for report in rows:
            report.status = ReportStatus.FAILED.value
            report.step = "Failed"
            report.error = STRANDED_ERROR
            report.completed_at = utc_now()
            session.add(report)
        if rows:
            session.commit()
    return len(rows)
