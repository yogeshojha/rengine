"""Writing an export, and clearing up after one."""

from __future__ import annotations

import time
import zipfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.exports import (
    BUNDLE,
    BUNDLE_EXTENSION,
    EXPORT_ROOT,
    FORMAT_EXTENSIONS,
    RETENTION_DAYS,
    STALE_AFTER_SECONDS,
    ExportStatus,
)
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension
from shared.logging import get_logger
from shared.models.export import Export
from shared.services.asset_export import runner
from shared.services.asset_query import QueryScope
from shared.services.surface_scope_sync import project_scope, target_scope
from shared.utils.datetime import utc_now
from shared.utils.slug import generate_slug

logger = get_logger(__name__)

_CLEANUP_BATCH = 500
_BUNDLE_DIMENSIONS = tuple(
    d for d in SURFACE_ORDER if d != SurfaceDimension.SOFTWARE.value
)


def _root(export_id: UUID) -> Path:
    path = Path(EXPORT_ROOT) / str(export_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stem(row: Export) -> str:
    subject = row.subject or row.dimension
    return generate_slug(f"{row.dimension}-{subject}")[:80] or "export"


@shared_task(bind=True, name="app.tasks.export.run", max_retries=0)
def run_export(self, export_id: str) -> None:
    session = get_sync_session()
    started = time.monotonic()
    try:
        row = session.get(Export, UUID(export_id))
        if row is None:
            logger.warning("export missing", export_id=export_id)
            return
        row.status = ExportStatus.RUNNING.value
        row.started_at = utc_now()
        row.task_id = self.request.id
        row.progress = 5
        row.step = "Starting"
        row.error = None
        session.commit()

        def progress(percent: int, label: str) -> None:
            row.progress = percent
            row.step = label
            session.commit()

        scope = _scope(session, row)
        now = utc_now()
        directory = _root(row.id)
        if row.dimension == BUNDLE:
            filename, written, total, capped = _write_bundle(
                session, row, scope, now, directory, progress
            )
        else:
            extension = FORMAT_EXTENSIONS.get(row.export_format, "csv")
            path = directory / f"{_stem(row)}.{extension}"
            result = runner.run(
                session,
                dimension=row.dimension,
                scope=scope,
                filters=row.filters or {},
                now=now,
                export_format=row.export_format,
                path=path,
                project_id=row.project_id,
                on_progress=progress,
            )
            filename = path.name
            written, total, capped = result.rows, result.total, result.capped

        row.filename = filename
        row.bytes_written = (directory / filename).stat().st_size
        row.row_count = written
        row.total_rows = total
        row.capped = capped
        row.status = ExportStatus.COMPLETED.value
        row.progress = 100
        row.step = "Ready"
        row.completed_at = utc_now()
        row.duration_seconds = round(time.monotonic() - started, 2)
        row.expires_at = utc_now() + timedelta(days=RETENTION_DAYS)
        session.commit()
    except Exception as exc:
        _fail(session, export_id, exc)
    finally:
        session.close()


def _scope(session, row: Export) -> QueryScope:
    """Resolved now, not when the export was saved, so a re-run reads today's scans."""
    dimension = (
        SurfaceDimension.WEB_ASSETS.value if row.dimension == BUNDLE else row.dimension
    )
    if row.scan_id is not None:
        return QueryScope((row.scan_id,), project_id=row.project_id)
    if row.target_id is not None:
        return target_scope(session, row.project_id, row.target_id, dimension)
    return project_scope(session, row.project_id, dimension)


def _write_bundle(session, row, scope, now, directory: Path, progress) -> tuple:
    """One file per dimension the scan produced, in one archive."""
    stem = _stem(row)
    archive = directory / f"{stem}.{BUNDLE_EXTENSION}"
    extension = FORMAT_EXTENSIONS.get(row.export_format, "csv")
    written = total = 0
    capped = False
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for index, dimension in enumerate(_BUNDLE_DIMENSIONS):
            progress(
                10 + int(80 * index / len(_BUNDLE_DIMENSIONS)),
                f"Writing {dimension.replace('_', ' ')}",
            )
            part = directory / f"{dimension}.{extension}"
            part_scope = (
                scope if row.scan_id else _dimension_scope(session, row, dimension)
            )
            result = runner.run(
                session,
                dimension=dimension,
                scope=part_scope,
                filters={},
                now=now,
                export_format=row.export_format,
                path=part,
                project_id=row.project_id,
            )
            written += result.rows
            total += result.total
            capped = capped or result.capped
            bundle.write(part, arcname=part.name)
            part.unlink(missing_ok=True)
    return archive.name, written, total, capped


def _dimension_scope(session, row: Export, dimension: str) -> QueryScope:
    if row.target_id is not None:
        return target_scope(session, row.project_id, row.target_id, dimension)
    return project_scope(session, row.project_id, dimension)


def _fail(session, export_id: str, exc: Exception) -> None:
    """The progress commits poisoned the session, so roll back before recording."""
    session.rollback()
    row = session.get(Export, UUID(export_id))
    if row is None:
        return
    row.status = ExportStatus.FAILED.value
    row.error = str(exc)[:2000]
    row.step = "Failed"
    row.completed_at = utc_now()
    session.commit()
    logger.warning("export failed", export_id=export_id, error=str(exc))


@shared_task(name="app.tasks.export.cleanup")
def cleanup() -> int:
    """An expired export keeps its recipe and loses its file."""
    session = get_sync_session()
    try:
        rows = (
            session.execute(
                select(Export)
                .where(
                    Export.status == ExportStatus.COMPLETED.value,
                    Export.expires_at.isnot(None),
                    Export.expires_at <= utc_now(),
                )
                .limit(_CLEANUP_BATCH)
            )
            .scalars()
            .all()
        )
        for row in rows:
            _purge(row.id)
            row.status = ExportStatus.EXPIRED.value
            row.filename = None
            row.bytes_written = 0
            row.step = "Expired"
        session.commit()
        return len(rows)
    finally:
        session.close()


@shared_task(name="app.tasks.export.reap")
def reap() -> int:
    """A run the worker lost never finishes on its own."""
    session = get_sync_session()
    try:
        cutoff = utc_now() - timedelta(seconds=STALE_AFTER_SECONDS)
        rows = (
            session.execute(
                select(Export).where(
                    Export.status.in_(
                        (ExportStatus.QUEUED.value, ExportStatus.RUNNING.value)
                    ),
                    Export.created_at <= cutoff,
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            row.status = ExportStatus.FAILED.value
            row.step = "Failed"
            row.error = "The export stopped without finishing. Run it again."
            row.completed_at = utc_now()
        session.commit()
        return len(rows)
    finally:
        session.close()


def _purge(export_id: UUID) -> None:
    directory = Path(EXPORT_ROOT) / str(export_id)
    if not directory.exists():
        return
    for item in directory.iterdir():
        item.unlink(missing_ok=True)
    directory.rmdir()
