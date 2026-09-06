from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.config import settings
from app.core.database import get_session
from mcp.models import (
    McpCallRead,
    McpSettingsUpdate,
    McpStatus,
    McpTokenCreate,
    McpTokenCreated,
    McpTokenRead,
    McpToolRead,
)
from mcp.service import McpConfigError, McpService
from mcp.transport import handle_request

router = APIRouter(prefix="/mcp", tags=["mcp"])

Session = Annotated[AsyncSession, Depends(get_session)]


def ui_base() -> str:
    return (
        settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
    )


def _guard(exc: McpConfigError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("", include_in_schema=False)
@router.post("/", include_in_schema=False)
async def mcp_endpoint(
    session: Session,
    payload: Annotated[dict | list, Body()],
    authorization: Annotated[str | None, Header()] = None,
    user_agent: Annotated[str | None, Header()] = None,
):
    """The protocol endpoint agents talk to. Authenticated by MCP service token."""
    response = await handle_request(
        payload,
        session=session,
        authorization=authorization,
        ui_base_url=ui_base(),
        client_hint=(user_agent or "unknown")[:120],
    )
    return response if response is not None else {}


@router.get("/status", response_model=McpStatus)
async def mcp_status(_current_user: CurrentUser, session: Session):
    return await McpService(session).status(ui_base())


@router.patch("/settings", response_model=McpStatus)
async def update_mcp(
    _admin: CurrentSuperuser, session: Session, body: McpSettingsUpdate
):
    try:
        await McpService(session).update(body)
    except McpConfigError as exc:
        raise _guard(exc) from exc
    return await McpService(session).status(ui_base())


@router.get("/tools", response_model=list[McpToolRead])
async def mcp_tools(_current_user: CurrentUser, session: Session):
    return McpService(session).tools()


@router.get("/calls", response_model=list[McpCallRead])
async def mcp_calls(
    _current_user: CurrentUser,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    return await McpService(session).calls(limit)


@router.get("/tokens", response_model=list[McpTokenRead])
async def mcp_tokens(_admin: CurrentSuperuser, session: Session):
    return await McpService(session).tokens()


@router.post(
    "/tokens", response_model=McpTokenCreated, status_code=status.HTTP_201_CREATED
)
async def create_mcp_token(
    admin: CurrentSuperuser, session: Session, body: McpTokenCreate
):
    try:
        return await McpService(session).create_token(body, admin.id, ui_base())
    except McpConfigError as exc:
        raise _guard(exc) from exc


@router.post("/tokens/{token_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_mcp_token(_admin: CurrentSuperuser, session: Session, token_id: UUID):
    try:
        await McpService(session).revoke_token(token_id)
    except McpConfigError as exc:
        raise _guard(exc) from exc


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_token(_admin: CurrentSuperuser, session: Session, token_id: UUID):
    try:
        await McpService(session).delete_token(token_id)
    except McpConfigError as exc:
        raise _guard(exc) from exc


@router.post("/sessions/{token_id}/disconnect", response_model=dict)
async def disconnect_mcp_session(
    _admin: CurrentSuperuser, session: Session, token_id: UUID
):
    return {"dropped": await McpService(session).disconnect(token_id)}
