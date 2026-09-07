from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.threat_intel import ThreatIntelService
from shared.definitions.threat_intel import (
    EXPLOIT_BANDS,
    FEEDS,
    MAX_EXPLOIT_SCORE,
    SIGNALS,
)
from shared.models.threat_intel import (
    AutoSyncUpdate,
    CveIntelRead,
    FindingIntel,
    IntelChange,
    SignalFinding,
    SyncResult,
    ThreatIntelStatus,
)
from shared.services.celery_dispatch import (
    dispatch_threat_intel,
    dispatch_threat_intel_refresh,
)

router = APIRouter(prefix="/threat-intel", tags=["threat intelligence"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThreatIntelService:
    return ThreatIntelService(session)


@router.get("/vocabulary")
async def vocabulary(_current_user: CurrentUser) -> dict:
    """The exploitation vocabulary the UI renders from."""
    return {
        "feeds": [
            {
                "kind": f.kind,
                "label": f.label,
                "tagline": f.tagline,
                "description": f.description,
                "source": f.source,
                "source_url": f.source_url,
                "url": f.url,
                "license": f.license,
            }
            for f in FEEDS
        ],
        "bands": [
            {
                "key": b.key,
                "label": b.label,
                "floor": b.floor,
                "description": b.description,
            }
            for b in EXPLOIT_BANDS
        ],
        "signals": [
            {
                "kind": s.kind,
                "label": s.label,
                "help": s.help,
                "weight": s.weight,
                "tone": s.tone,
            }
            for s in SIGNALS
        ],
        "max_score": MAX_EXPLOIT_SCORE,
    }


@router.get("/status", response_model=ThreatIntelStatus)
async def status(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    project_id: Annotated[UUID | None, Query()] = None,
) -> ThreatIntelStatus:
    return await service.status(project_id)


@router.get("/changes", response_model=list[IntelChange])
async def changes(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    project_id: Annotated[UUID | None, Query()] = None,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[IntelChange]:
    return await service.changes(project_id, days=days, limit=limit)


@router.put("/auto-sync", response_model=ThreatIntelStatus)
async def set_auto_sync(
    _current_user: CurrentSuperuser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    body: AutoSyncUpdate,
    project_id: Annotated[UUID | None, Query()] = None,
) -> ThreatIntelStatus:
    """Turn the nightly download on or off. Manual refresh keeps working either way."""
    await service.set_auto_sync(body.enabled)
    return await service.status(project_id)


@router.post("/sync", response_model=SyncResult)
async def sync(_current_user: CurrentSuperuser) -> SyncResult:
    """Download the feeds now and re-rank every finding, whatever the switch says."""
    queued = dispatch_threat_intel_refresh(force=True)
    return SyncResult(
        queued=queued,
        feeds=[f.kind for f in FEEDS],
        detail=None
        if queued
        else "The task queue did not accept the refresh. Check the worker.",
    )


@router.post("/scan/{scan_id}/enrich", response_model=SyncResult)
async def enrich(
    _current_user: CurrentUser,
    scan_id: Annotated[UUID, Path()],
) -> SyncResult:
    """Fill the provider cache for this scan's CVEs, then re-rank on the richer data."""
    dispatch_threat_intel(str(scan_id))
    return SyncResult(queued=True, feeds=["vulnx"])


@router.get("/cve/{cve_id}", response_model=CveIntelRead)
async def cve(
    _current_user: CurrentUser,
    service: Annotated[ThreatIntelService, Depends(get_service)],
    cve_id: Annotated[str, Path(max_length=30)],
) -> CveIntelRead:
    return await service.cve(cve_id)


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
    project_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SignalFinding]:
    """The findings behind one signal count, so the number opens its own rows."""
    return await service.signal_findings(kind, project_id, limit=limit)
