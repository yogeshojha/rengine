from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.bounty_program import BountyProgramService
from app.services.instance_settings import InstanceSettingsService
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
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS, has_capability
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
SessionDep = Annotated[AsyncSession, Depends(get_session)]
PlatformPath = Annotated[str, Path(description="Bug bounty platform key")]


async def _require_mode(session: AsyncSession) -> None:
    """The library is a bug bounty capability; corporate mode does not carry it."""
    settings = await InstanceSettingsService(session).get_or_create()
    if not has_capability(settings.mode, CAP_BOUNTY_PROGRAMS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bug bounty programs are available in bug bounty mode.",
        )


@router.get("/vocabulary")
async def vocabulary(_current_user: CurrentUser) -> dict:
    """Platforms, asset types and states the library renders from."""
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
    """What changed in the library, newest first."""
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
    """Clear the unseen badge once the feed has been read."""
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
    """How often reNgine syncs, and which changes are worth an alert."""
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
    scopes: bool = Query(True, description="Also refresh every program's scope"),
) -> dict:
    """Queue a refresh of the program library."""
    await _require_mode(session)
    BountyProgramService.require_platform(platform)
    state = await service.status(platform)
    if not state.configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a HackerOne API username and token first.",
        )
    return {"queued": dispatch_bounty_sync(scopes=scopes)}


@router.post("/sync-feed")
async def sync_feed(
    session: SessionDep,
    _current_user: CurrentSuperuser,
) -> dict:
    """Queue a refresh of the public program feed. Needs no credentials."""
    await _require_mode(session)
    return {"queued": dispatch_bounty_feed_sync()}


@router.get("")
async def list_programs(
    session: SessionDep,
    service: ServiceDep,
    _current_user: CurrentUser,
    platform: str | None = Query(None, description="a single platform key"),
    platforms: Annotated[list[str] | None, Query()] = None,
    sources: Annotated[list[str] | None, Query()] = None,
    q: str | None = Query(None),
    state: str | None = Query(None, description="public or private"),
    submission: str | None = Query(None, description="open, paused or closed"),
    bounty: bool | None = Query(None),
    bookmarked: bool | None = Query(None),
    joined: bool | None = Query(None, description="programs you are a member of"),
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
    _current_user: CurrentUser,
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
