import re
from uuid import UUID

import yaml
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan_context import usage_counts
from app.services.scan_engine.validation import (
    _MAX_YAML_LEN,
    _check_tool_options_access,
    _full_stages,
    _mask_global_headers,
    _mask_tool_options,
    _unmask_global_headers,
    _unmask_tool_options,
    _validate_global_headers,
    _validate_intensity,
    _validate_stages,
    _validate_tool_options,
    _validate_yaml_source,
    _without_secret_keys,
)
from shared.definitions.default_engine import (
    DEFAULT_ENGINE_DESCRIPTION,
    DEFAULT_ENGINE_INTENSITY,
    DEFAULT_ENGINE_NAME,
    default_engine_stages,
)
from shared.definitions.launch import CREDENTIAL_CHANGE, ENGINE_NOUN
from shared.enums.scan import SCAN_OPEN_STATUSES, Intensity
from shared.models.scan import Scan
from shared.models.scan_engine import (
    EngineUsage,
    ScanEngine,
    ScanEngineCreate,
    ScanEngineRead,
    ScanEngineUpdate,
)
from shared.services.credential_access import (
    engine_carries_credentials,
    may_use,
    plain_tool_options,
)
from shared.utils.datetime import utc_now
from shared.utils.yaml_safe import DocumentTooLargeError, load_document

_ENGINE_KEYS = frozenset(
    {
        "name",
        "description",
        "intensity",
        "global_headers",
        "stages",
        "transport_overrides",
        "tool_options",
    }
)

_NAME_LINE = re.compile(r"^name:[^\n]*(?:\n[ \t]+[^\n]*)*", re.MULTILINE)


def _renamed_source(source: str | None, name: str) -> str | None:
    """Rewrite the top-level name of a stored engine document."""
    if not source:
        return source
    line = yaml.safe_dump({"name": name}, allow_unicode=True, width=1 << 16).rstrip()
    renamed, count = _NAME_LINE.subn(lambda _: line, source, count=1)
    return renamed if count else None


def _to_read(
    engine: ScanEngine, usage: EngineUsage | None = None, *, superuser: bool = False
) -> ScanEngineRead:
    return ScanEngineRead(
        usage=usage or EngineUsage(),
        id=engine.id,
        project_id=engine.project_id,
        created_by=engine.created_by,
        name=engine.name,
        description=engine.description,
        intensity=engine.intensity,
        global_headers=_mask_global_headers(engine.global_headers or []),
        stages=dict(engine.stages or {}),
        transport_overrides=dict(engine.transport_overrides or {}),
        yaml_source=_without_secret_keys(engine.yaml_source),
        tool_options=_mask_tool_options(engine.tool_options, superuser=superuser),
        builtin=bool(engine.builtin),
        carries_credentials=engine_carries_credentials(engine),
        created_at=engine.created_at,
        updated_at=engine.updated_at,
        last_used_at=engine.last_used_at,
    )


def _check_change(
    engine: ScanEngine, actor_id: UUID | None, superuser: bool, *, gains: bool = False
) -> None:
    if actor_id is None or may_use(engine.created_by, actor_id, superuser):
        return
    if gains or engine_carries_credentials(engine):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=CREDENTIAL_CHANGE.format(noun=ENGINE_NOUN, name=engine.name),
        )


async def _running_scans_for(session: AsyncSession, engine_id: UUID) -> int:
    rows = await session.execute(
        select(func.count())
        .select_from(Scan)
        .where(Scan.engine_id == engine_id, Scan.status.in_(SCAN_OPEN_STATUSES))
    )
    return rows.scalar_one()


async def _usage_for(
    session: AsyncSession, engine_ids: list[UUID]
) -> dict[UUID, EngineUsage]:
    return await usage_counts(session, "engine_id", engine_ids, EngineUsage)


class ScanEngineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        project_id: UUID,
        created_by: UUID,
        data: ScanEngineCreate,
        *,
        superuser: bool = False,
    ) -> ScanEngineRead:
        _validate_global_headers(data.global_headers)
        _validate_intensity(data.intensity)
        tool_options = _validate_tool_options(data.tool_options)
        _check_tool_options_access(superuser, None, tool_options)

        engine = ScanEngine(
            project_id=project_id,
            created_by=created_by,
            name=data.name,
            description=data.description,
            intensity=data.intensity,
            global_headers=data.global_headers,
            stages=_validate_stages(data.stages),
            transport_overrides=dict(data.transport_overrides or {}),
            yaml_source=_validate_yaml_source(data.yaml_source),
            tool_options=tool_options,
        )
        self.session.add(engine)
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine, superuser=superuser)

    async def ensure_builtin(self, project_id: UUID, created_by: UUID) -> ScanEngine:
        """The project's built-in engine, created on first sight."""
        existing = await self._builtin_for(project_id)
        if existing is not None:
            return existing
        engine = ScanEngine(
            project_id=project_id,
            created_by=created_by,
            name=DEFAULT_ENGINE_NAME,
            description=DEFAULT_ENGINE_DESCRIPTION,
            intensity=DEFAULT_ENGINE_INTENSITY,
            stages=_validate_stages(default_engine_stages()),
            builtin=True,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(engine)
                await self.session.flush()
        except IntegrityError:
            raced = await self._builtin_for(project_id)
            if raced is None:
                raise
            return raced
        return engine

    async def _builtin_for(self, project_id: UUID) -> ScanEngine | None:
        result = await self.session.execute(
            select(ScanEngine).where(
                ScanEngine.project_id == project_id, ScanEngine.builtin.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id: UUID,
        created_by: UUID | None = None,
        *,
        superuser: bool = False,
    ) -> list[ScanEngineRead]:
        if created_by is not None:
            await self.ensure_builtin(project_id, created_by)
            await self.session.commit()
        result = await self.session.execute(
            select(ScanEngine)
            .where(ScanEngine.project_id == project_id)
            .order_by(ScanEngine.updated_at.desc())
        )
        engines = list(result.scalars().all())
        usage = await _usage_for(self.session, [e.id for e in engines])
        return [_to_read(e, usage.get(e.id), superuser=superuser) for e in engines]

    async def get(
        self, id: UUID, project_id: UUID, *, superuser: bool = False
    ) -> ScanEngineRead:
        engine = await self._get_or_404(id, project_id)
        usage = await _usage_for(self.session, [engine.id])
        return _to_read(engine, usage.get(engine.id), superuser=superuser)

    async def update(
        self,
        id: UUID,
        project_id: UUID,
        data: ScanEngineUpdate,
        *,
        superuser: bool = False,
        actor_id: UUID | None = None,
    ) -> ScanEngineRead:
        engine = await self._get_or_404(id, project_id)
        _check_change(engine, actor_id, superuser, gains=bool(data.global_headers))
        tool_options = None
        if data.tool_options is not None:
            tool_options = _validate_tool_options(
                _unmask_tool_options(data.tool_options, engine.tool_options)
            )
            _check_tool_options_access(superuser, engine.tool_options, tool_options)

        if data.name is not None:
            engine.name = data.name
        if data.description is not None:
            engine.description = data.description
        if data.intensity is not None:
            _validate_intensity(data.intensity)
            engine.intensity = data.intensity
        if data.global_headers is not None:
            restored = _unmask_global_headers(
                data.global_headers, engine.global_headers or []
            )
            _validate_global_headers(restored)
            engine.global_headers = restored
        if data.stages is not None:
            engine.stages = _validate_stages(data.stages)
        if data.transport_overrides is not None:
            engine.transport_overrides = dict(data.transport_overrides)
        if data.yaml_source is not None:
            engine.yaml_source = _validate_yaml_source(data.yaml_source)
        if tool_options is not None:
            engine.tool_options = tool_options

        engine.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine, superuser=superuser)

    async def delete(
        self,
        id: UUID,
        project_id: UUID,
        *,
        superuser: bool = False,
        actor_id: UUID | None = None,
    ) -> bool:
        engine = await self._get_or_404(id, project_id)
        _check_change(engine, actor_id, superuser)
        if engine.builtin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{engine.name} is built in and is not deleted.",
            )
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
        self, id: UUID, project_id: UUID, created_by: UUID, *, superuser: bool = False
    ) -> ScanEngineRead:
        original = await self._get_or_404(id, project_id)
        keep = may_use(original.created_by, created_by, superuser)

        copy_name = f"{original.name} (copy)"
        engine = ScanEngine(
            project_id=project_id,
            created_by=created_by,
            name=copy_name,
            description=original.description,
            intensity=original.intensity,
            global_headers=list(original.global_headers or []) if keep else [],
            stages=dict(original.stages or {}),
            transport_overrides=dict(original.transport_overrides or {}),
            yaml_source=_renamed_source(
                _without_secret_keys(original.yaml_source), copy_name
            ),
            tool_options=dict(original.tool_options or {})
            if keep
            else plain_tool_options(original.tool_options),
        )
        self.session.add(engine)
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine, superuser=superuser)

    async def export_yaml(
        self, id: UUID, project_id: UUID, *, superuser: bool = False
    ) -> str:
        engine = await self._get_or_404(id, project_id)
        data = {
            "name": engine.name,
            "description": engine.description,
            "intensity": engine.intensity,
            "global_headers": _mask_global_headers(engine.global_headers or []),
            "stages": _full_stages(engine.stages),
            "transport_overrides": dict(engine.transport_overrides or {}),
            "tool_options": _mask_tool_options(
                engine.tool_options, superuser=superuser
            ),
        }
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    async def import_yaml(
        self,
        project_id: UUID,
        created_by: UUID,
        yaml_str: str,
        *,
        superuser: bool = False,
    ) -> ScanEngineRead:
        if yaml_str and len(yaml_str) > _MAX_YAML_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Engine YAML may not exceed {_MAX_YAML_LEN} characters.",
            )
        try:
            data = load_document(yaml_str)
        except DocumentTooLargeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML: {e}",
            ) from e

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YAML must be a mapping",
            )

        if "name" not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YAML must include a 'name' field",
            )

        unknown = [k for k in data if k not in _ENGINE_KEYS]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown top-level key {', '.join(repr(u) for u in sorted(unknown))}. "
                    f"Valid keys: {', '.join(sorted(_ENGINE_KEYS))}, with stage settings under 'stages'."
                ),
            )

        try:
            create_data = ScanEngineCreate(
                name=str(data["name"]),
                description=data.get("description"),
                intensity=data.get("intensity", Intensity.NORMAL.value),
                global_headers=list(data.get("global_headers") or []),
                stages=dict(data.get("stages") or {}),
                transport_overrides=dict(data.get("transport_overrides") or {}),
                tool_options=dict(data.get("tool_options") or {}),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid engine config: {e}",
            ) from e

        return await self.create(
            project_id, created_by, create_data, superuser=superuser
        )

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
