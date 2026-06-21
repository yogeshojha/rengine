from uuid import UUID

import yaml
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.scan_engine import (
    DepthConfig,
    DiscoveryConfig,
    ExpansionConfig,
    ScanEngine,
    ScanEngineCreate,
    ScanEngineRead,
    ScanEngineUpdate,
)
from shared.services.scan_resolve import _SENSITIVE_HEADER, MASK, _reject_ctrl
from shared.utils.datetime import utc_now

_MAX_HEADERS = 1000
_MAX_HEADER_LEN = 4096
_MAX_YAML_LEN = 512 * 1024

_INTENSITIES = {"passive", "normal", "aggressive"}
_MAX_ENGINE_THREADS = 1000


def _validate_intensity(intensity: str | None) -> None:
    if intensity is not None and intensity not in _INTENSITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"intensity must be one of {sorted(_INTENSITIES)}.",
        )


def _validate_global_threads(threads: int | None) -> None:
    if threads is not None and not (1 <= threads <= _MAX_ENGINE_THREADS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"global_threads must be between 1 and {_MAX_ENGINE_THREADS}.",
        )


def _validate_global_headers(headers: list) -> None:
    if headers and len(headers) > _MAX_HEADERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"global_headers may not exceed {_MAX_HEADERS} entries.",
        )
    for line in headers or []:
        if isinstance(line, str) and len(line) > _MAX_HEADER_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Each global header may not exceed {_MAX_HEADER_LEN} characters.",
            )
        if not isinstance(line, str) or ":" not in line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each global header must be a 'Name: Value' string.",
            )
        name, value = line.split(":", 1)
        if not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each global header must have a non-empty name.",
            )
        _reject_ctrl("Header name", name)
        _reject_ctrl("Header value", value)


def _mask_global_headers(headers: list) -> list[str]:
    out: list[str] = []
    for line in headers or []:
        if isinstance(line, str) and ":" in line:
            name, value = line.split(":", 1)
            if value.strip() and _SENSITIVE_HEADER.search(name.strip()):
                out.append(f"{name.strip()}: {MASK}")
                continue
        out.append(line)
    return out


def _unmask_global_headers(incoming: list, stored: list) -> list[str]:
    stored_map: dict[str, str] = {}
    for line in stored or []:
        if isinstance(line, str) and ":" in line:
            name, value = line.split(":", 1)
            stored_map[name.strip().lower()] = value.strip()
    out: list[str] = []
    for line in incoming or []:
        if isinstance(line, str) and ":" in line:
            name, value = line.split(":", 1)
            if value.strip() == MASK and name.strip().lower() in stored_map:
                out.append(f"{name.strip()}: {stored_map[name.strip().lower()]}")
                continue
        out.append(line)
    return out


def _mask_depth(depth: dict) -> dict:
    out = dict(depth or {})
    if out.get("report_webhook_url"):
        out["report_webhook_url"] = MASK
    return out


def _unmask_depth(incoming: dict, stored: dict) -> dict:
    out = dict(incoming or {})
    if MASK in (out.get("report_webhook_url") or ""):
        out["report_webhook_url"] = (stored or {}).get("report_webhook_url")
    return out


def _to_read(engine: ScanEngine) -> ScanEngineRead:
    discovery = DiscoveryConfig(**(engine.discovery or {}))
    expansion = ExpansionConfig(**(engine.expansion or {}))
    depth = DepthConfig(**_mask_depth(engine.depth or {}))
    return ScanEngineRead(
        id=engine.id,
        project_id=engine.project_id,
        created_by=engine.created_by,
        name=engine.name,
        description=engine.description,
        intensity=engine.intensity,
        global_threads=engine.global_threads,
        global_http_crawl=engine.global_http_crawl,
        global_headers=_mask_global_headers(engine.global_headers or []),
        discovery=discovery,
        expansion=expansion,
        depth=depth,
        created_at=engine.created_at,
        updated_at=engine.updated_at,
        last_used_at=engine.last_used_at,
    )


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
        discovery = (data.discovery or DiscoveryConfig()).model_dump()
        expansion = (data.expansion or ExpansionConfig()).model_dump()
        depth = (data.depth or DepthConfig()).model_dump()

        engine = ScanEngine(
            project_id=project_id,
            created_by=created_by,
            name=data.name,
            description=data.description,
            intensity=data.intensity,
            global_threads=data.global_threads,
            global_http_crawl=data.global_http_crawl,
            global_headers=data.global_headers,
            discovery=discovery,
            expansion=expansion,
            depth=depth,
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
        engines = result.scalars().all()
        return [_to_read(e) for e in engines]

    async def get(self, id: UUID, project_id: UUID) -> ScanEngineRead:
        engine = await self._get_or_404(id, project_id)
        return _to_read(engine)

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
        if data.discovery is not None:
            engine.discovery = data.discovery.model_dump()
        if data.expansion is not None:
            engine.expansion = data.expansion.model_dump()
        if data.depth is not None:
            engine.depth = _unmask_depth(data.depth.model_dump(), engine.depth or {})

        engine.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(engine)
        return _to_read(engine)

    async def delete(self, id: UUID, project_id: UUID) -> bool:
        engine = await self._get_or_404(id, project_id)
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
            discovery=dict(original.discovery or {}),
            expansion=dict(original.expansion or {}),
            depth=dict(original.depth or {}),
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
            "discovery": engine.discovery or {},
            "expansion": engine.expansion or {},
            "depth": _mask_depth(engine.depth or {}),
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

        try:
            discovery_raw = data.get("discovery") or {}
            expansion_raw = data.get("expansion") or {}
            depth_raw = data.get("depth") or {}
            if isinstance(depth_raw, dict) and MASK in (
                depth_raw.get("report_webhook_url") or ""
            ):
                depth_raw = {**depth_raw, "report_webhook_url": None}

            discovery = DiscoveryConfig(**discovery_raw)
            expansion = ExpansionConfig(**expansion_raw)
            depth = DepthConfig(**depth_raw)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scan engine config structure: {e}",
            ) from e

        create_data = ScanEngineCreate(
            name=str(data["name"]),
            description=data.get("description"),
            intensity=data.get("intensity", "normal"),
            global_threads=int(data.get("global_threads", 30)),
            global_http_crawl=bool(data.get("global_http_crawl", True)),
            global_headers=list(data.get("global_headers") or []),
            discovery=discovery,
            expansion=expansion,
            depth=depth,
        )

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
