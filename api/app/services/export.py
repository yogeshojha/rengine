"""Exports: creating one, listing them, and handing the file back."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select

from shared.definitions.exports import (
    BUNDLE,
    EXPORT_FORMATS,
    EXPORT_ROOT,
    LIVE_STATUSES,
    MAX_RUNNING_PER_PROJECT,
    ExportScope,
    ExportStatus,
)
from shared.definitions.surface import EXPORTABLE_DIMENSIONS, SURFACE_LABELS
from shared.models.export import Export, ExportCreate, ExportRead
from shared.models.scan import Scan
from shared.models.target import Target
from shared.services.celery_dispatch import dispatch_export

MAX_LIST = 100


class ExportService:
    def __init__(self, session) -> None:
        self.session = session

    async def create(
        self, data: ExportCreate, project_id: UUID, created_by: UUID | None
    ) -> ExportRead:
        if data.dimension != BUNDLE and data.dimension not in EXPORTABLE_DIMENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.dimension}' cannot be exported.",
            )
        if data.export_format not in EXPORT_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.export_format}' is not an export format.",
            )
        await self._check_capacity(project_id)
        scope, subject = await self._subject(data, project_id)

        row = Export(
            project_id=project_id,
            created_by=created_by,
            dimension=data.dimension,
            scope=scope,
            scan_id=data.scan_id,
            target_id=data.target_id,
            subject=subject,
            query=(data.filters or {}).get("q") or "",
            filters=data.filters or {},
            export_format=data.export_format,
            include_evidence=data.include_evidence,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        dispatch_export(str(row.id))
        return self._read(row)

    async def rerun(self, export_id: UUID, project_id: UUID) -> ExportRead:
        """Run the export's recipe again."""
        original = await self._get(export_id, project_id)
        await self._check_capacity(project_id)
        row = Export(
            project_id=project_id,
            created_by=original.created_by,
            dimension=original.dimension,
            scope=original.scope,
            scan_id=original.scan_id,
            target_id=original.target_id,
            subject=original.subject,
            query=original.query,
            filters=original.filters,
            export_format=original.export_format,
            include_evidence=original.include_evidence,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        dispatch_export(str(row.id))
        return self._read(row)

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> list[ExportRead]:
        statement = select(Export).where(Export.project_id == project_id)
        if scan_id is not None:
            statement = statement.where(Export.scan_id == scan_id)
        elif target_id is not None:
            statement = statement.where(Export.target_id == target_id)
        rows = (
            await self.session.execute(
                statement.order_by(Export.created_at.desc()).limit(MAX_LIST)
            )
        ).scalars()
        return [self._read(row) for row in rows]

    async def get(self, export_id: UUID, project_id: UUID) -> ExportRead:
        return self._read(await self._get(export_id, project_id))

    async def delete(self, export_id: UUID, project_id: UUID) -> None:
        row = await self._get(export_id, project_id)
        _purge(row.id)
        await self.session.delete(row)
        await self.session.commit()

    async def file_path(self, export_id: UUID, project_id: UUID) -> tuple[Path, str]:
        row = await self._get(export_id, project_id)
        if row.status != ExportStatus.COMPLETED.value or not row.filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The export has no file. Run it again.",
            )
        path = _resolve(row.id, row.filename)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The export has no file. Run it again.",
            )
        return path, row.filename

    async def _check_capacity(self, project_id: UUID) -> None:
        running = (
            await self.session.execute(
                select(func.count())
                .select_from(Export)
                .where(
                    Export.project_id == project_id,
                    Export.status.in_(LIVE_STATUSES),
                )
            )
        ).scalar_one()
        if running >= MAX_RUNNING_PER_PROJECT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{running} exports are already running. Wait for one to finish."
                ),
            )

    async def _subject(self, data: ExportCreate, project_id: UUID) -> tuple[str, str]:
        label = SURFACE_LABELS.get(data.dimension, "All dimensions")
        if data.scan_id is not None:
            scan = await self.session.get(Scan, data.scan_id)
            if scan is None or scan.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
                )
            target = await self.session.get(Target, scan.target_id)
            return ExportScope.SCAN.value, target.target_value if target else label
        if data.target_id is not None:
            target = await self.session.get(Target, data.target_id)
            if target is None or target.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Target not found"
                )
            return ExportScope.TARGET.value, target.target_value
        return ExportScope.PROJECT.value, label

    async def _get(self, export_id: UUID, project_id: UUID) -> Export:
        row = await self.session.get(Export, export_id)
        if row is None or row.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
            )
        return row

    @staticmethod
    def _read(row: Export) -> ExportRead:
        return ExportRead.model_validate(row, from_attributes=True)


def _resolve(export_id: UUID, filename: str) -> Path | None:
    """Resolve the export's file under the export root."""
    root = Path(EXPORT_ROOT).resolve()
    path = (root / str(export_id) / filename).resolve()
    if not path.is_relative_to(root) or not path.exists():
        return None
    return path


def _purge(export_id: UUID) -> None:
    directory = Path(EXPORT_ROOT) / str(export_id)
    if not directory.exists():
        return
    for item in directory.iterdir():
        item.unlink(missing_ok=True)
    directory.rmdir()
