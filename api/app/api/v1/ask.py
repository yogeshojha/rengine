from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, StreamUser
from app.api.scope import TargetFilterDep, VulnScope
from app.api.v1.events import STREAM_HEADERS
from app.core.database import async_db_session, get_session
from app.services.ask.estate import service as estate
from app.services.ask.estate.service import EstateService
from app.services.ask.service import AskService, stream_reply
from shared.definitions.ask import ASK_DIMENSIONS, BLOCK_ID
from shared.definitions.notes import MAX_ASSET_KEY
from shared.definitions.surface import SurfaceDimension
from shared.models.ask import (
    AskBrief,
    AskQuestion,
    AskThreadCreate,
    AskThreadDetail,
    AskThreadRead,
    BlockData,
    BlockQueryEdit,
    EstateQuestion,
    EstateScanOption,
    EstateStarters,
    EstateStatus,
    EstateThreadCreate,
    EstateThreadDetail,
    EstateThreadRead,
)

router = APIRouter(prefix="/ask", tags=["ask"])
Session = Annotated[AsyncSession, Depends(get_session)]


def get_service(session: Session) -> AskService:
    return AskService(session)


Service = Annotated[AskService, Depends(get_service)]


def get_estate(session: Session) -> EstateService:
    return EstateService(session)


Estate = Annotated[EstateService, Depends(get_estate)]
ProjectId = Annotated[UUID, Query(description="Project ID")]
ThreadId = Annotated[UUID, Path(description="Thread ID")]
BlockId = Annotated[
    str, Path(pattern=BLOCK_ID.pattern, max_length=4, description="Block ID")
]


@router.get("/brief/web-asset", response_model=AskBrief)
async def brief_asset(
    _user: CurrentUser,
    service: Service,
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    name: Annotated[str, Query(min_length=1, max_length=MAX_ASSET_KEY)],
):
    found = await service.brief_asset(scan_id, name)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Web asset not found.")
    return found


@router.get("/brief/{vulnerability_id}", response_model=AskBrief)
async def brief(
    _user: CurrentUser,
    service: Service,
    vulnerability_id: Annotated[UUID, Path(description="Vulnerability ID")],
    scope: VulnScope,
):
    found = await service.brief(scope, vulnerability_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found.")
    return found


AssetKey = Annotated[
    str, Query(min_length=1, max_length=MAX_ASSET_KEY, description="Asset key")
]
Dimension = Annotated[
    str, Query(max_length=32, description="Result dimension the asset belongs to")
]


def _dimension(value: str) -> str:
    if value not in ASK_DIMENSIONS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Ask is not offered on that dimension.",
        )
    return value


@router.get("/threads", response_model=list[AskThreadRead])
async def list_threads(
    user: CurrentUser,
    service: Service,
    target_id: Annotated[UUID, Query(description="Target ID")],
    asset_key: AssetKey,
    dimension: Dimension = SurfaceDimension.VULNERABILITIES.value,
):
    return await service.threads(user.id, target_id, _dimension(dimension), asset_key)


@router.post(
    "/threads", response_model=AskThreadRead, status_code=status.HTTP_201_CREATED
)
async def create_thread(
    data: AskThreadCreate,
    user: CurrentUser,
    service: Service,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.create(user.id, project_id, data)


@router.delete("/threads")
async def delete_threads(
    user: CurrentUser,
    service: Service,
    target_id: Annotated[UUID, Query(description="Target ID")],
    asset_key: AssetKey,
    dimension: Dimension = SurfaceDimension.VULNERABILITIES.value,
) -> dict[str, int]:
    return {
        "deleted": await service.delete_all(
            user.id, target_id, _dimension(dimension), asset_key
        )
    }


@router.get("/threads/{thread_id}", response_model=AskThreadDetail)
async def get_thread(
    user: CurrentUser,
    service: Service,
    thread_id: Annotated[UUID, Path(description="Thread ID")],
):
    found = await service.detail(user.id, thread_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    return found


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    user: CurrentUser,
    service: Service,
    thread_id: Annotated[UUID, Path(description="Thread ID")],
):
    if not await service.delete(user.id, thread_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")


@router.post("/threads/{thread_id}/messages")
async def ask(
    data: AskQuestion,
    user: StreamUser,
    thread_id: Annotated[UUID, Path(description="Thread ID")],
):
    async with async_db_session() as session:
        owned = await AskService(session).get(user.id, thread_id) is not None
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    return StreamingResponse(
        stream_reply(thread_id=thread_id, user=user, question=data),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )


# ---------- the estate ----------


@router.get("/estate/status", response_model=EstateStatus)
async def estate_status(_user: CurrentUser, service: Estate):
    return await service.status()


@router.get("/estate/starters", response_model=EstateStarters)
async def estate_starters(
    _user: CurrentUser,
    service: Estate,
    project_id: ProjectId,
    spec: TargetFilterDep,
    scan_id: UUID | None = None,
):
    raw = {
        "target_ids": [str(t) for t in spec.target_ids],
        "organization_id": str(spec.organization_id) if spec.organization_id else None,
        "tag_id": str(spec.tag_id) if spec.tag_id else None,
        "scan_id": str(scan_id) if scan_id else None,
    }
    return await service.starters(project_id, raw)


@router.get("/estate/scans", response_model=list[EstateScanOption])
async def estate_scans(
    _user: CurrentUser,
    service: Estate,
    project_id: ProjectId,
    spec: TargetFilterDep,
    search: Annotated[str, Query(max_length=100)] = "",
):
    return await service.scans(project_id, spec, search)


@router.get("/estate/threads", response_model=list[EstateThreadRead])
async def estate_threads(user: CurrentUser, service: Estate, project_id: ProjectId):
    return await service.threads(user.id, project_id)


@router.post(
    "/estate/threads",
    response_model=EstateThreadRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_estate_thread(
    data: EstateThreadCreate, user: CurrentUser, service: Estate, project_id: ProjectId
):
    return await service.create(user.id, project_id, data)


@router.get("/estate/threads/{thread_id}", response_model=EstateThreadDetail)
async def get_estate_thread(user: CurrentUser, service: Estate, thread_id: ThreadId):
    found = await service.detail(user.id, thread_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    return found


@router.get("/estate/threads/{thread_id}/blocks", response_model=list[BlockData])
async def estate_blocks(user: CurrentUser, service: Estate, thread_id: ThreadId):
    found = await service.blocks(user.id, thread_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    return found


@router.get("/estate/threads/{thread_id}/blocks/{block_id}", response_model=BlockData)
async def estate_block_page(
    user: CurrentUser,
    service: Estate,
    thread_id: ThreadId,
    block_id: BlockId,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
):
    return await service.page(user.id, thread_id, block_id, offset)


@router.put(
    "/estate/threads/{thread_id}/blocks/{block_id}/query", response_model=BlockData
)
async def edit_estate_block(
    data: BlockQueryEdit,
    user: CurrentUser,
    service: Estate,
    thread_id: ThreadId,
    block_id: BlockId,
):
    return await service.edit(user.id, thread_id, block_id, data.query)


@router.delete("/estate/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_estate_thread(user: CurrentUser, service: Estate, thread_id: ThreadId):
    if not await service.delete(user.id, thread_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")


@router.post("/estate/threads/{thread_id}/messages")
async def ask_estate(data: EstateQuestion, user: StreamUser, thread_id: ThreadId):
    async with async_db_session() as session:
        owned = await EstateService(session).get(user.id, thread_id) is not None
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    return StreamingResponse(
        estate.stream_reply(thread_id=thread_id, user=user, question=data),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
