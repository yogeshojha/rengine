from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.api.errors import bad_request
from app.config import settings
from app.core.client_ip import client_id
from app.core.database import get_session
from app.core.ratelimit import clear_failures, record_failure, too_many_attempts
from mcp.errors import UNAUTHORIZED
from mcp.models import (
    McpCallRead,
    McpSettingsUpdate,
    McpStatus,
    McpTokenCreate,
    McpTokenCreated,
    McpTokenRead,
    McpTokenUpdate,
    McpToolRead,
)
from mcp.service import McpConfigError, McpService
from mcp.transport import DISABLED_MESSAGE, handle_request

router = APIRouter(prefix="/mcp", tags=["mcp"])

Session = Annotated[AsyncSession, Depends(get_session)]

TOKEN_ATTEMPT_LIMIT = 20
TOKEN_ATTEMPT_WINDOW = 900


def ui_base() -> str:
    return settings.ui_base_url


def _rejected_token(response: dict | list | None) -> bool:
    if not isinstance(response, dict):
        return False
    error = response.get("error")
    if not isinstance(error, dict) or error.get("code") != UNAUTHORIZED:
        return False
    return error.get("message") != DISABLED_MESSAGE


def _answered(response: dict | list | None) -> bool:
    return not isinstance(response, dict) or "error" not in response


@router.post("", include_in_schema=False)
@router.post("/", include_in_schema=False)
async def mcp_endpoint(
    session: Session,
    request: Request,
    payload: Annotated[dict | list, Body()],
    authorization: Annotated[str | None, Header()] = None,
    user_agent: Annotated[str | None, Header()] = None,
):
    """MCP protocol endpoint. Authenticated by service token."""
    key = f"mcp:token:{client_id(request)}"
    await too_many_attempts(key, limit=TOKEN_ATTEMPT_LIMIT)
    response = await handle_request(
        payload,
        session=session,
        authorization=authorization,
        ui_base_url=ui_base(),
        client_hint=(user_agent or "unknown")[:120],
    )
    if _rejected_token(response):
        await record_failure(key, window_seconds=TOKEN_ATTEMPT_WINDOW)
    elif _answered(response):
        await clear_failures(key)
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
        raise bad_request(exc) from exc
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
        raise bad_request(exc) from exc


@router.patch("/tokens/{token_id}", response_model=McpTokenRead)
async def update_mcp_token(
    _admin: CurrentSuperuser, session: Session, token_id: UUID, body: McpTokenUpdate
):
    try:
        return await McpService(session).update_token(token_id, body)
    except McpConfigError as exc:
        raise bad_request(exc) from exc


@router.post("/tokens/{token_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_mcp_token(_admin: CurrentSuperuser, session: Session, token_id: UUID):
    try:
        await McpService(session).revoke_token(token_id)
    except McpConfigError as exc:
        raise bad_request(exc) from exc


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_token(_admin: CurrentSuperuser, session: Session, token_id: UUID):
    try:
        await McpService(session).delete_token(token_id)
    except McpConfigError as exc:
        raise bad_request(exc) from exc
