from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from channels.models import (
    ChannelCatalogEntry,
    ChannelChatRead,
    ChannelChatUpdate,
    ChannelCommandRead,
    ChannelConnect,
    ChannelSettingsUpdate,
    ChannelStatus,
    ChannelVerifyResult,
    PairingApprove,
    PairingRequestRead,
)
from channels.service import (
    ChannelConfigError,
    ChannelNotFoundError,
    ChannelService,
    catalog,
)
from mcp.models import McpCallRead

router = APIRouter(prefix="/remote-control", tags=["remote-control"])

Session = Annotated[AsyncSession, Depends(get_session)]


def _service(session: AsyncSession, channel: str) -> ChannelService:
    try:
        return ChannelService(session, channel)
    except ChannelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


def _guard(exc: ChannelConfigError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/channels", response_model=list[ChannelCatalogEntry])
async def list_channels(_current_user: CurrentUser, session: Session):
    return await catalog(session)


@router.get("/channels/{channel}/status", response_model=ChannelStatus)
async def channel_status(_current_user: CurrentUser, session: Session, channel: str):
    return await _service(session, channel).status()


@router.patch("/channels/{channel}/settings", response_model=ChannelStatus)
async def update_channel(
    admin: CurrentSuperuser,
    session: Session,
    channel: str,
    body: ChannelSettingsUpdate,
):
    try:
        return await _service(session, channel).update(body, admin.id)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.post("/channels/{channel}/connect", response_model=ChannelStatus)
async def connect_channel(
    admin: CurrentSuperuser, session: Session, channel: str, body: ChannelConnect
):
    try:
        return await _service(session, channel).connect(body.token, admin.id)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.post("/channels/{channel}/disconnect", response_model=ChannelStatus)
async def disconnect_channel(admin: CurrentSuperuser, session: Session, channel: str):
    return await _service(session, channel).disconnect(admin.id)


@router.post("/channels/{channel}/verify", response_model=ChannelVerifyResult)
async def verify_channel(_admin: CurrentSuperuser, session: Session, channel: str):
    return await _service(session, channel).verify()


@router.get("/channels/{channel}/pending", response_model=list[PairingRequestRead])
async def pending_pairings(_admin: CurrentSuperuser, session: Session, channel: str):
    return await _service(session, channel).pending()


@router.post(
    "/channels/{channel}/pending/{code}/approve",
    response_model=ChannelChatRead,
    status_code=status.HTTP_201_CREATED,
)
async def approve_pairing(
    admin: CurrentSuperuser,
    session: Session,
    channel: str,
    code: str,
    body: PairingApprove,
):
    try:
        return await _service(session, channel).approve(code, body, admin.id)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.post(
    "/channels/{channel}/pending/{code}/block", status_code=status.HTTP_204_NO_CONTENT
)
async def block_pairing(
    admin: CurrentSuperuser, session: Session, channel: str, code: str
):
    try:
        await _service(session, channel).block(code, admin.id)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.get("/channels/{channel}/chats", response_model=list[ChannelChatRead])
async def list_chats(_admin: CurrentSuperuser, session: Session, channel: str):
    return await _service(session, channel).chats()


@router.patch("/channels/{channel}/chats/{chat_id}", response_model=ChannelChatRead)
async def update_chat(
    _admin: CurrentSuperuser,
    session: Session,
    channel: str,
    chat_id: UUID,
    body: ChannelChatUpdate,
):
    try:
        return await _service(session, channel).update_chat(chat_id, body)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.post(
    "/channels/{channel}/chats/{chat_id}/revoke", response_model=ChannelChatRead
)
async def revoke_chat(
    _admin: CurrentSuperuser, session: Session, channel: str, chat_id: UUID
):
    try:
        return await _service(session, channel).revoke_chat(chat_id)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.delete(
    "/channels/{channel}/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_chat(
    _admin: CurrentSuperuser, session: Session, channel: str, chat_id: UUID
):
    try:
        await _service(session, channel).delete_chat(chat_id)
    except ChannelConfigError as exc:
        raise _guard(exc) from exc


@router.get("/channels/{channel}/commands", response_model=list[ChannelCommandRead])
async def list_commands(_current_user: CurrentUser, session: Session, channel: str):
    return _service(session, channel).commands()


@router.get("/channels/{channel}/calls", response_model=list[McpCallRead])
async def list_calls(
    _current_user: CurrentUser,
    session: Session,
    channel: str,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
):
    return await _service(session, channel).calls(limit)
