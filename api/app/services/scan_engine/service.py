from uuid import UUID

import yaml
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan_engine.validation import (
    _MAX_YAML_LEN,
    _full_stages,
    _mask_global_headers,
    _mask_tool_options,
    _unmask_global_headers,
    _unmask_tool_options,
    _validate_global_headers,
    _validate_global_threads,
    _validate_intensity,
    _validate_stages,
    _validate_tool_options,
    _validate_yaml_source,
)
from shared.enums.scan import SCAN_LIVE_STATUSES
from shared.models.scan import Scan
from shared.models.scan_engine import (
    EngineUsage,
    ScanEngine,
    ScanEngineCreate,
    ScanEngineRead,
    ScanEngineUpdate,
)
from shared.models.scan_schedule import ScanSchedule
from shared.utils.datetime import utc_now

_ENGINE_KEYS = frozenset(
    {
        "name",
        "description",
        "intensity",
        "global_threads",
        "global_headers",
        "stages",
        "tool_options",
    }
)


def _to_read(engine: ScanEngine, usage: EngineUsage | None = None) -> ScanEngineRead:
    return ScanEngineRead(
        usage=usage or EngineUsage(),
        id=engine.id,
        project_id=engine.project_id,
        created_by=engine.created_by,
        name=engine.name,
        description=engine.description,
        intensity=engine.intensity,
        global_threads=engine.global_threads,
        global_http_crawl=engine.global_http_crawl,
        global_headers=_mask_global_headers(engine.global_headers or []),
        stages=dict(engine.stages or {}),
        yaml_source=engine.yaml_source,
        tool_options=_mask_tool_options(engine.tool_options),
        created_at=engine.created_at,
        updated_at=engine.updated_at,
        last_used_at=engine.last_used_at,
    )


async def _running_scans_for(session: AsyncSession, engine_id: UUID) -> int:
    rows = await session.execute(
        select(func.count())
        .select_from(Scan)
        .where(Scan.engine_id == engine_id, Scan.status.in_(SCAN_LIVE_STATUSES))
    )
    return rows.scalar_one()


async def _usage_for(
    session: AsyncSession, engine_ids: list[UUID]
) -> dict[UUID, EngineUsage]:
    """How many schedules and scans depend on each engine — edits and deletes are not free."""
    out = {eid: EngineUsage() for eid in engine_ids}
    if not engine_ids:
        return out
    for model, field in ((ScanSchedule, "schedules"), (Scan, "scans")):
        rows = await session.execute(
            select(model.engine_id, func.count())
            .where(model.engine_id.in_(engine_ids))
            .group_by(model.engine_id)
        )
        for engine_id, count in rows.all():
            setattr(out[engine_id], field, count)
    return out


class ScanEngineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        project_id: UUID,
        created_by: UUID,
        data: ScanEngineCreate,
    ) -> ScanEngineRead:
        _validate_global_headers(data.global_headers)
        _validate_intensity(data.intensity)
        _validate_global_threads(data.global_threads)

        engine = ScanEngine(
            project_id=project_id,
            created_by=created_by,
            name=data.name,
            description=data.description,
            intensity=data.intensity,
            global_threads=data.global_threads,
            global_http_crawl=data.global_http_crawl,
            global_headers=data.global_headers,
            stages=_validate_stages(data.stages),
            yaml_source=_validate_yaml_source(data.yaml_source),
            tool_options=_validate_tool_options(data.tool_options),
        )
        self.session.add(engine)
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine)

    async def list(self, project_id: UUID) -> list[ScanEngineRead]:
        result = await self.session.execute(
            select(ScanEngine)
            .where(ScanEngine.project_id == project_id)
            .order_by(ScanEngine.updated_at.desc())
        )
        engines = list(result.scalars().all())
        usage = await _usage_for(self.session, [e.id for e in engines])
        return [_to_read(e, usage.get(e.id)) for e in engines]

    async def get(self, id: UUID, project_id: UUID) -> ScanEngineRead:
        engine = await self._get_or_404(id, project_id)
        usage = await _usage_for(self.session, [engine.id])
        return _to_read(engine, usage.get(engine.id))

    async def update(
        self,
        id: UUID,
        project_id: UUID,
        data: ScanEngineUpdate,
    ) -> ScanEngineRead:
        engine = await self._get_or_404(id, project_id)

        if data.name is not None:
            engine.name = data.name
        if data.description is not None:
            engine.description = data.description
        if data.intensity is not None:
            _validate_intensity(data.intensity)
            engine.intensity = data.intensity
        if data.global_threads is not None:
            _validate_global_threads(data.global_threads)
            engine.global_threads = data.global_threads
        if data.global_http_crawl is not None:
            engine.global_http_crawl = data.global_http_crawl
        if data.global_headers is not None:
            _validate_global_headers(data.global_headers)
            engine.global_headers = _unmask_global_headers(
                data.global_headers, engine.global_headers or []
            )
        if data.stages is not None:
            engine.stages = _validate_stages(data.stages)
        if data.yaml_source is not None:
            engine.yaml_source = _validate_yaml_source(data.yaml_source)
        if data.tool_options is not None:
            engine.tool_options = _validate_tool_options(
                _unmask_tool_options(data.tool_options, engine.tool_options)
            )

        engine.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine)

    async def delete(self, id: UUID, project_id: UUID) -> bool:
        engine = await self._get_or_404(id, project_id)
        running = await _running_scans_for(self.session, engine.id)
        if running:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{engine.name}' is in use by {running} running "
                    f"scan{'s' if running != 1 else ''}. Cancel them first."
                ),
            )
        usage = (await _usage_for(self.session, [engine.id]))[engine.id]
        if usage.schedules:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{engine.name}' is used by {usage.schedules} "
                    f"scheduled scan{'s' if usage.schedules != 1 else ''}. "
                    "Detach or delete those schedules first."
                ),
            )
        await self.session.delete(engine)
        await self.session.commit()
        return True

    async def duplicate(
        self, id: UUID, project_id: UUID, created_by: UUID
    ) -> ScanEngineRead:
        original = await self._get_or_404(id, project_id)

        copy_name = f"{original.name} (copy)"
        engine = ScanEngine(
            project_id=project_id,
            created_by=created_by,
            name=copy_name,
            description=original.description,
            intensity=original.intensity,
            global_threads=original.global_threads,
            global_http_crawl=original.global_http_crawl,
            global_headers=list(original.global_headers or []),
            stages=dict(original.stages or {}),
            yaml_source=original.yaml_source,
            tool_options=dict(original.tool_options or {}),
        )
        self.session.add(engine)
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine)

    async def export_yaml(self, id: UUID, project_id: UUID) -> str:
        engine = await self._get_or_404(id, project_id)
        data = {
            "name": engine.name,
            "description": engine.description,
            "intensity": engine.intensity,
            "global_threads": engine.global_threads,
            "global_http_crawl": engine.global_http_crawl,
            "global_headers": _mask_global_headers(engine.global_headers or []),
            "stages": _full_stages(engine.stages),
            "tool_options": _mask_tool_options(engine.tool_options),
        }
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    async def import_yaml(
        self, project_id: UUID, created_by: UUID, yaml_str: str
    ) -> ScanEngineRead:
        if yaml_str and len(yaml_str) > _MAX_YAML_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"YAML payload may not exceed {_MAX_YAML_LEN} bytes.",
            )
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML: {e}",
            ) from e

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YAML must represent a mapping/object",
            )

        if "name" not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YAML must include a 'name' field",
            )

        # a mis-indented stage lands here as a top-level key — never accept it silently
        unknown = [k for k in data if k not in _ENGINE_KEYS]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown top-level key {', '.join(repr(u) for u in sorted(unknown))}. "
                    f"Expected: {', '.join(sorted(_ENGINE_KEYS))}. "
                    "A stage must be nested under 'stages:'."
                ),
            )

        try:
            create_data = ScanEngineCreate(
                name=str(data["name"]),
                description=data.get("description"),
                intensity=data.get("intensity", "normal"),
                global_threads=int(data.get("global_threads", 30)),
                global_http_crawl=bool(data.get("global_http_crawl", True)),
                global_headers=list(data.get("global_headers") or []),
                stages=dict(data.get("stages") or {}),
                yaml_source=yaml_str,
                tool_options=dict(data.get("tool_options") or {}),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scan engine config structure: {e}",
            ) from e

        return await self.create(project_id, created_by, create_data)

    async def touch(self, id: UUID, project_id: UUID) -> None:
        engine = await self._get_or_404(id, project_id)
        engine.last_used_at = utc_now()
        await self.session.commit()

    async def _get_or_404(self, id: UUID, project_id: UUID) -> ScanEngine:
        result = await self.session.execute(
            select(ScanEngine).where(
                ScanEngine.id == id,
                ScanEngine.project_id == project_id,
            )
        )
        engine = result.scalar_one_or_none()
        if not engine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan engine not found",
            )
        return engine
