from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.api.scope import TargetFilterDep, resolve_scope
from app.core.database import get_session
from app.services.target_scope import TargetFilter
from app.services.threat_intel import ThreatIntelService
from shared.definitions.surface import SurfaceDimension
from shared.definitions.threat_intel import FEEDS
from shared.models.threat_intel import (
    AutoSyncUpdate,
    FindingIntel,
    IntelChange,
    SignalFinding,
    SyncResult,
    ThreatIntelStatus,
)
from shared.services.asset_query import QueryScope
from shared.services.celery_dispatch import dispatch_threat_intel_refresh

router = APIRouter(prefix="/threat-intel", tags=["threat intelligence"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThreatIntelService:
    return ThreatIntelService(session)


async def _findings_scope(
    session: AsyncSession, project_id: UUID | None, spec: TargetFilter
) -> QueryScope | None:
    if project_id is None:
        return None
    return await resolve_scope(
        session, SurfaceDimension.VULNERABILITIES.value, None, project_id, spec
    )


@router.get("/status", response_model=ThreatIntelStatus)
async def status(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID | None, Query()] = None,
) -> ThreatIntelStatus:
    scope = await _findings_scope(service.session, project_id, spec)
    return await service.status(scope)


@router.get("/changes", response_model=list[IntelChange])
async def changes(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID | None, Query()] = None,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[IntelChange]:
    scope = await _findings_scope(service.session, project_id, spec)
    return await service.changes(scope, days=days, limit=limit)


@router.put("/auto-sync", response_model=ThreatIntelStatus)
async def set_auto_sync(
    _current_user: CurrentSuperuser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    body: AutoSyncUpdate,
    project_id: Annotated[UUID | None, Query()] = None,
) -> ThreatIntelStatus:
    """Turn the nightly download on or off."""
    await service.set_auto_sync(body.enabled)
    scope = await _findings_scope(service.session, project_id, TargetFilter())
    return await service.status(scope)


@router.post("/sync", response_model=SyncResult)
async def sync(_current_user: CurrentSuperuser) -> SyncResult:
    """Download the feeds and re-rank every finding."""
    queued = dispatch_threat_intel_refresh()
    return SyncResult(
        queued=queued,
        feeds=[f.kind for f in FEEDS],
        detail=None
        if queued
        else "The task queue did not accept the sync. Check the worker.",
    )


@router.get("/finding/{vulnerability_id}", response_model=FindingIntel)
async def finding(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    vulnerability_id: Annotated[UUID, Path()],
) -> FindingIntel:
    return await service.finding(vulnerability_id)


@router.get("/signal/{kind}", response_model=list[SignalFinding])
async def signal_findings(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    kind: Annotated[str, Path(max_length=32)],
    spec: TargetFilterDep,
    project_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SignalFinding]:
    """Findings behind one signal count."""
    scope = await _findings_scope(service.session, project_id, spec)
    return await service.signal_findings(kind, scope, limit=limit)
