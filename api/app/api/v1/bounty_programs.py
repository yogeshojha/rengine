from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.bounty_program import BountyProgramService
from app.services.instance_settings import InstanceSettingsService
from app.services.watch import WatchService, validate_alert_query
from shared.definitions.bounty_programs import (
    ASSET_TYPES,
    EVENTS,
    MAX_SEVERITIES,
    PLATFORMS,
    AssetGroup,
    BountyPlatform,
    ProgramState,
    ScopeState,
    SubmissionState,
    SyncInterval,
)
from shared.definitions.mode_features import (
    CAP_BOUNTY_PROGRAMS,
    CAP_PROGRAM_WATCHES,
    has_capability,
)
from shared.models.bounty_program import (
    BountyEventRead,
    BountyImportRequest,
    BountyImportResult,
    BountyProgramDetail,
    BountyProgramRead,
    BountySettingsRead,
    BountySettingsUpdate,
    BountyStatus,
)
from shared.models.watch import (
    StreamStatus,
    WatchCreate,
    WatchEventRead,
    WatchHostCounts,
    WatchHostRead,
    WatchPreview,
    WatchRead,
    WatchUpdate,
)
from shared.services.celery_dispatch import (
    dispatch_bounty_feed_sync,
    dispatch_bounty_program_sync,
    dispatch_bounty_sync,
)

router = APIRouter(prefix="/bounty-programs", tags=["bounty programs"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BountyProgramService:
    return BountyProgramService(session)


ServiceDep = Annotated[BountyProgramService, Depends(get_service)]


def get_watches(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WatchService:
    return WatchService(session)


WatchDep = Annotated[WatchService, Depends(get_watches)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
PlatformPath = Annotated[str, Path(description="Bug bounty platform key")]


async def _require_mode(session: AsyncSession) -> None:
    """Bug bounty mode gate."""
    settings = await InstanceSettingsService(session).get_or_create()
    if not has_capability(settings.mode, CAP_BOUNTY_PROGRAMS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bug bounty programs require bug bounty mode.",
        )


@router.get("/vocabulary")
async def vocabulary(_current_user: CurrentUser) -> dict:
    """Bounty program vocabulary."""
    return {
        "platforms": [
            {
                "key": p.key,
                "label": p.label,
                "url": p.url,
                "supports_private": p.supports_private,
                "note": p.note,
            }
            for p in PLATFORMS
        ],
        "asset_types": [
            {
                "key": a.key,
                "label": a.label,
                "group": a.group.value,
                "icon": a.icon,
                "note": a.note,
                "targetable": a.targetable,
                "target_type": a.target_type.value if a.target_type else None,
            }
            for a in ASSET_TYPES
        ],
        "asset_groups": [g.value for g in AssetGroup],
        "program_states": [s.value for s in ProgramState],
        "submission_states": [s.value for s in SubmissionState],
        "scope_states": [s.value for s in ScopeState],
        "max_severities": list(MAX_SEVERITIES),
        "events": [
            {
                "kind": e.kind,
                "label": e.label,
                "description": e.description,
                "icon": e.icon,
                "tone": e.tone,
                "actionable": e.actionable,
            }
            for e in EVENTS
        ],
        "sync_intervals": [i.value for i in SyncInterval],
    }


@router.get("/events")
async def list_events(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
    platform: str | None = Query(None),
    kind: str | None = Query(None),
    handle: str | None = Query(None),
) -> Page[BountyEventRead]:
    """Program library events, newest first."""
    await _require_mode(session)
    if platform:
        BountyProgramService.require_platform(platform)
    query = await service.events(platform, kind=kind, handle=handle)
    page = await paginate(session, query)
    page.items = [BountyProgramService.event_read(r) for r in page.items]
    return page


@router.post("/events/seen")
async def mark_events_seen(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> dict:
    """Mark every event seen."""
    await _require_mode(session)
    await service.mark_events_seen()
    return {"ok": True}


@router.get("/settings")
async def read_settings(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
    platform: str = Query(BountyPlatform.HACKERONE.value),
) -> BountySettingsRead:
    """Sync interval and alert settings."""
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    return await service.read_settings()


@router.put("/settings")
async def write_settings(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentSuperuser,
    data: BountySettingsUpdate,
    platform: str = Query(BountyPlatform.HACKERONE.value),
) -> BountySettingsRead:
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    return await service.write_settings(data)


@router.get("/status")
async def get_status(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
    platform: str = Query(BountyPlatform.HACKERONE.value),
) -> BountyStatus:
    await _require_mode(session)
    return await service.status(BountyProgramService.require_platform(platform))


@router.post("/sync")
async def sync(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentSuperuser,
    platform: str = Query(BountyPlatform.HACKERONE.value),
    scopes: bool = Query(True, description="Refresh every program's scope"),
) -> dict:
    """Queue a refresh of the program library."""
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    state = await service.status(platform)
    if not state.configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HackerOne API username and token are not set. Add them under API keys.",
        )
    return {"queued": dispatch_bounty_sync(scopes=scopes)}


@router.post("/sync-feed")
async def sync_feed(
    session: SessionDep,
    _current_user: CurrentSuperuser,
) -> dict:
    """Queue a refresh of the public program feed."""
    await _require_mode(session)
    return {"queued": dispatch_bounty_feed_sync()}


@router.get("")
async def list_programs(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
    platform: str | None = Query(None, description="Platform key"),
    platforms: Annotated[list[str] | None, Query()] = None,
    sources: Annotated[list[str] | None, Query()] = None,
    q: str | None = Query(None),
    state: str | None = Query(None, description="public or private"),
    submission: str | None = Query(None, description="open, paused or closed"),
    bounty: bool | None = Query(None),
    bookmarked: bool | None = Query(None),
    joined: bool | None = Query(None, description="Member programs only"),
    scope: str | None = Query(None, description="importable or none"),
    sort: str = Query("age"),
    project_id: Annotated[UUID | None, Query()] = None,
) -> Page[BountyProgramRead]:
    await _require_mode(session)
    if platform:
        BountyProgramService.require_platform(platform)
    query = service.list_query(
        platform,
        sort=sort,
        platforms=platforms,
        sources=sources,
        q=q,
        state=state,
        submission=submission,
        bounty=bounty,
        bookmarked=bookmarked,
        joined=joined,
        scope=scope,
    )
    page = await paginate(session, query)
    page.items = await service.to_read(list(page.items), project_id)
    return page


async def _require_watches(session: AsyncSession) -> None:
    """Program watches are a bug bounty mode capability."""
    settings = await InstanceSettingsService(session).get_or_create()
    if not has_capability(settings.mode, CAP_PROGRAM_WATCHES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Program watches require bug bounty mode.",
        )


# ---------- watches ----------


class AlertQueryCheck(BaseModel):
    query: str = ""


@router.post("/watches/validate-query")
async def validate_query(
    body: AlertQueryCheck, _current_user: CurrentUser, session: SessionDep
) -> dict:
    await _require_watches(session)
    return {"error": validate_alert_query(body.query)}


@router.get("/watches/stream", response_model=StreamStatus)
async def stream_status(
    _current_user: CurrentUser, session: SessionDep
) -> StreamStatus:
    await _require_watches(session)
    return await WatchService.stream_status()


@router.get("/watches", response_model=list[WatchRead])
async def list_watches(
    project_id: UUID, current_user: CurrentUser, watches: WatchDep, session: SessionDep
) -> list[WatchRead]:
    await _require_watches(session)
    return await watches.list(project_id, current_user.id)


@router.get("/watches/{watch_id}", response_model=WatchRead)
async def get_watch(
    watch_id: UUID,
    project_id: UUID,
    current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> WatchRead:
    await _require_watches(session)
    return await watches.get(watch_id, project_id, current_user.id)


@router.patch("/watches/{watch_id}", response_model=WatchRead)
async def update_watch(
    watch_id: UUID,
    project_id: UUID,
    data: WatchUpdate,
    current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> WatchRead:
    await _require_watches(session)
    return await watches.update(watch_id, project_id, data, current_user.id)


@router.delete("/watches/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch(
    watch_id: UUID,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> None:
    await _require_watches(session)
    await watches.delete(watch_id, project_id)


@router.post("/watches/{watch_id}/seen")
async def mark_watch_seen(
    watch_id: UUID,
    project_id: UUID,
    current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> dict:
    await _require_watches(session)
    at = await watches.mark_seen(watch_id, project_id, current_user.id)
    return {"seen_at": at}


@router.post("/watches/{watch_id}/reconcile")
async def reconcile_watch(
    watch_id: UUID,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> dict:
    await _require_watches(session)
    return await watches.reconcile(watch_id, project_id)


@router.get("/watches/{watch_id}/hosts", response_model=Page[WatchHostRead])
async def list_watch_hosts(
    watch_id: UUID,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
    state: Annotated[str | None, Query(max_length=32)] = None,
    since: datetime | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> Page[WatchHostRead]:
    await _require_watches(session)
    await watches.ensure(watch_id, project_id)
    return await paginate(
        session,
        watches.hosts_query(watch_id, state=state, since=since, q=q),
        transformer=lambda rows: [WatchService.host_read(r) for r in rows],
    )


@router.get("/watches/{watch_id}/hosts/counts", response_model=WatchHostCounts)
async def watch_host_counts(
    watch_id: UUID,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
    since: datetime | None = None,
) -> WatchHostCounts:
    await _require_watches(session)
    return await watches.host_counts(watch_id, project_id, since)


@router.post("/watches/{watch_id}/hosts/{host_id}/mute", response_model=WatchHostRead)
async def mute_watch_host(
    watch_id: UUID,
    host_id: UUID,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> WatchHostRead:
    await _require_watches(session)
    return await watches.mute_host(watch_id, host_id, project_id)


@router.get("/watches/{watch_id}/events", response_model=Page[WatchEventRead])
async def list_watch_events(
    watch_id: UUID,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
    kind: Annotated[str | None, Query(max_length=32)] = None,
    since: datetime | None = None,
) -> Page[WatchEventRead]:
    await _require_watches(session)
    await watches.ensure(watch_id, project_id)
    return await paginate(
        session,
        watches.events_query(watch_id, kind=kind, since=since),
        transformer=lambda rows: [WatchService.event_read(r) for r in rows],
    )


@router.get("/{platform}/{handle}/watch/preview", response_model=WatchPreview)
async def watch_preview(
    platform: PlatformPath,
    handle: str,
    project_id: UUID,
    _current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> WatchPreview:
    await _require_watches(session)
    return await watches.preview(
        BountyProgramService.require_platform(platform), handle, project_id
    )


@router.post("/{platform}/{handle}/watch", response_model=WatchRead)
async def create_watch(
    platform: PlatformPath,
    handle: str,
    data: WatchCreate,
    current_user: CurrentUser,
    watches: WatchDep,
    session: SessionDep,
) -> WatchRead:
    await _require_watches(session)
    return await watches.create(
        BountyProgramService.require_platform(platform), handle, data, current_user.id
    )


@router.get("/{platform}/{handle}")
async def program_detail(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
    platform: PlatformPath,
    handle: str,
    project_id: Annotated[UUID | None, Query()] = None,
    scope: str | None = Query(None, description="in_scope or out_of_scope"),
    asset_type: str | None = Query(None),
) -> BountyProgramDetail:
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    return await service.detail(
        platform, handle, project_id=project_id, scope=scope, asset_type=asset_type
    )


@router.post("/{platform}/{handle}/sync")
async def sync_program(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentSuperuser,
    platform: PlatformPath,
    handle: str,
) -> dict:
    """Refresh one program's scope."""
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    await service.get_program(platform, handle)
    return {"queued": dispatch_bounty_program_sync(handle, platform)}


@router.post("/{platform}/{handle}/import")
async def import_program(
    session: SessionDep,
    service: ServiceDep,
    current_user: CurrentUser,
    platform: PlatformPath,
    handle: str,
    request: BountyImportRequest,
) -> BountyImportResult:
    """Add the program's scannable assets to a project as targets."""
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    return await service.import_scopes(platform, handle, request, current_user.id)
