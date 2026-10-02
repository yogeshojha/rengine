import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.ai_settings import AiSettingsService, call_cursor
from shared.definitions.ai import MAX_CALLS_PAGE
from shared.models.ai import (
    AiCallPage,
    AiConnectionCreate,
    AiConnectionRead,
    AiConnectionUpdate,
    AiModelList,
    AiModelsRequest,
    AiSettingsUpdate,
    AiStatus,
    AiTestRequest,
    AiTestResult,
)

router = APIRouter(prefix="/ai", tags=["ai"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/status", response_model=AiStatus)
async def ai_status(current_user: CurrentUser, session: Session):
    return await AiSettingsService(session).status(full=current_user.is_superuser)


@router.get("/calls", response_model=AiCallPage)
async def recent_calls(
    _user: CurrentUser,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=MAX_CALLS_PAGE, description="Rows")] = (
        MAX_CALLS_PAGE
    ),
    before: Annotated[
        str | None,
        Query(
            max_length=100,
            description="The at and id of the last row of the previous page, "
            "joined by a comma",
        ),
    ] = None,
):
    return await AiSettingsService(session).calls(limit, call_cursor(before))


@router.get("/catalog", response_model=dict)
async def ai_catalog(_current_user: CurrentUser):
    return AiSettingsService.catalog()


@router.patch("/settings", response_model=AiStatus)
async def update_ai(_admin: CurrentSuperuser, session: Session, body: AiSettingsUpdate):
    return await AiSettingsService(session).update(body)


@router.get("/connections", response_model=list[AiConnectionRead])
async def list_connections(current_user: CurrentUser, session: Session):
    return await AiSettingsService(session).connections(full=current_user.is_superuser)


@router.post(
    "/connections",
    response_model=AiConnectionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    _admin: CurrentSuperuser, session: Session, body: AiConnectionCreate
):
    return await AiSettingsService(session).create_connection(body)


@router.patch("/connections/{connection_id}", response_model=AiConnectionRead)
async def update_connection(
    connection_id: uuid.UUID,
    _admin: CurrentSuperuser,
    session: Session,
    body: AiConnectionUpdate,
):
    return await AiSettingsService(session).update_connection(connection_id, body)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID, _admin: CurrentSuperuser, session: Session
):
    await AiSettingsService(session).delete_connection(connection_id)


@router.post("/connections/{connection_id}/use", response_model=AiConnectionRead)
async def use_connection(
    connection_id: uuid.UUID, _admin: CurrentSuperuser, session: Session
):
    return await AiSettingsService(session).use_connection(connection_id)


@router.post("/connections/{connection_id}/test", response_model=AiTestResult)
async def test_connection(
    connection_id: uuid.UUID, admin: CurrentSuperuser, session: Session
):
    return await AiSettingsService(session).test_connection(connection_id, admin.id)


@router.post("/models", response_model=AiModelList)
async def list_models(
    _admin: CurrentSuperuser, session: Session, body: AiModelsRequest
):
    return await AiSettingsService(session).models(body)


@router.post("/test", response_model=AiTestResult)
async def test_ai(admin: CurrentSuperuser, session: Session, body: AiTestRequest):
    return await AiSettingsService(session).test(body, admin.id)


@router.delete("/cache", response_model=dict)
async def clear_ai_cache(_admin: CurrentSuperuser, session: Session):
    removed = await AiSettingsService(session).clear_cache()
    return {"removed": removed}
