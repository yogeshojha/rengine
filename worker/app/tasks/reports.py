"""Report generation runs here so the api never blocks on a render."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from celery import shared_task

from app.config import settings
from app.database import get_sync_session
from reports import theme_store
from reports.pipeline import generate
from shared.definitions.reports import (
    FORMAT_EXTENSIONS,
    REPORT_ROOT,
    RETENTION_DAYS,
    ReportSpec,
    ReportStatus,
)
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.sse import SSEChannel, SSEEventType
from shared.logging import get_logger
from shared.models.report import Report
from shared.models.scan import Scan
from shared.models.target import Target
from shared.services.event_publisher import SyncEventPublisher
from shared.services.notification_sync import SyncNotificationPublisher
from shared.utils.datetime import utc_now
from shared.utils.slug import generate_slug

logger = get_logger(__name__)


def _root(report_id: UUID) -> Path:
    path = Path(REPORT_ROOT) / str(report_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _publisher() -> SyncEventPublisher | None:
    try:
        return SyncEventPublisher(settings.celery_broker_url)
    except Exception:
        logger.warning("report events unavailable")
        return None


def _announce(publisher, report: Report) -> None:
    if publisher is None:
        return
    payload = {
        "id": str(report.id),
        "status": report.status,
        "progress": report.progress,
        "step": report.step,
        "error": report.error,
        "page_count": report.page_count,
    }
    publisher.publish(
        SSEChannel.report(str(report.id)), SSEEventType.REPORT.value, payload
    )
    publisher.publish(
        SSEChannel.project(str(report.project_id)), SSEEventType.REPORT.value, payload
    )


@shared_task(bind=True, name="app.tasks.reports.generate", max_retries=0)
def generate_report(self, report_id: str) -> dict:
    started = time.monotonic()
    publisher = _publisher()

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
        _announce(publisher, report)

        def progress(percent: int, label: str) -> None:
            report.progress = percent
            report.step = label
            session.add(report)
            session.commit()
            _announce(publisher, report)

        try:
            spec = ReportSpec.model_validate(report.spec or {})
            scan, target = _subject(session, report)
            theme_store.sync_builtin(session)
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
            _announce(publisher, report)
            _notify(session, report, ok=True)
            logger.info(
                "report ready",
                report_id=report_id,
                pages=output.pages,
                seconds=report.duration_seconds,
            )
            return {"status": report.status, "pages": output.pages, "files": len(files)}

        except Exception as exc:
            _fail(
                session, publisher, report_id, exc, round(time.monotonic() - started, 2)
            )
            logger.exception("report failed", report_id=report_id)
            raise


def _fail(session, publisher, report_id: str, exc: Exception, seconds: float) -> None:
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
    _announce(publisher, report)
    _notify(session, report, ok=False)


def _subject(session, report: Report) -> tuple[Scan | None, Target]:
    target = session.get(Target, report.target_id) if report.target_id else None
    scan = session.get(Scan, report.scan_id) if report.scan_id else None
    if target is None and scan is not None:
        target = session.get(Target, scan.target_id)
    if target is None:
        msg = "The report has no target to describe."
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


def _notify(session, report: Report, *, ok: bool) -> None:
    name = report.title or report.template_name or "Report"
    body = (
        f"{name} for {report.subject} is ready to download."
        if ok
        else f"{name} for {report.subject} could not be generated: {report.error}"
    )
    try:
        SyncNotificationPublisher(settings.celery_broker_url).publish(
            session,
            NotificationType.SYSTEM,
            NotificationSeverity.SUCCESS if ok else NotificationSeverity.ERROR,
            "Report ready" if ok else "Report failed",
            body,
        )
    except Exception:
        logger.debug("report notification skipped", exc_info=True)


@shared_task(name="app.tasks.reports.cleanup")
def cleanup() -> dict:
    """Drop generated files past their retention date."""
    removed = 0
    with get_sync_session() as session:
        now = utc_now()
        rows = (
            session.query(Report)
            .filter(Report.expires_at.is_not(None), Report.expires_at < now)
            .limit(500)
            .all()
        )
        for report in rows:
            root = Path(REPORT_ROOT) / str(report.id)
            if root.exists():
                for item in root.iterdir():
                    item.unlink(missing_ok=True)
                root.rmdir()
            report.files = []
            report.status = ReportStatus.FAILED.value
            report.error = (
                "The generated files passed their retention date and were removed."
            )
            session.add(report)
            removed += 1
        if removed:
            session.commit()
    return {"removed": removed}
