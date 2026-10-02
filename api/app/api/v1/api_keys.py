from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser
from app.core.database import get_session
from channels.service import ChannelService
from channels.telegram.driver import TelegramError, valid_token
from channels.telegram.driver import verify as verify_bot
from shared.definitions.api_keys import API_PROVIDER_META
from shared.definitions.channels import PROVIDER_CHANNELS
from shared.enums.api_key import APIProvider
from shared.models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyRead,
    APIKeyUpdate,
    ProviderInfo,
)
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.bounty_providers import HackerOneProvider, IntigritiProvider
from shared.services.scan_resolve import MASK
from shared.utils.crypto import decrypt_stored
from tools.viewdns.client import ViewDNSClient


async def _test_viewdns(key_value: str, _key_meta: dict | None) -> dict:
    client = ViewDNSClient(key_value)
    _ = await client.ip_history("rengine.wiki")
    return {"message": "API key is valid."}


def _programs_seen(result: dict) -> str:
    count = result.get("programs_visible") or 0
    sample = result.get("sample_handle")
    if sample:
        return f" {count} programs visible, starting at @{sample}."
    return f" {count} programs visible."


async def _test_hackerone(key_value: str, key_meta: dict | None) -> dict:
    username = (key_meta or {}).get("username")
    if not username:
        msg = "HackerOne API username is missing. Add it with the token."
        raise ValueError(msg)
    provider = HackerOneProvider(str(username), key_value)
    result = await anyio.to_thread.run_sync(provider.verify)
    return {"message": f"Signed in to HackerOne as {username}.{_programs_seen(result)}"}


async def _test_intigriti(key_value: str, _key_meta: dict | None) -> dict:
    provider = IntigritiProvider(key_value)
    result = await anyio.to_thread.run_sync(provider.verify)
    return {"message": f"Signed in to Intigriti.{_programs_seen(result)}"}


async def _test_telegram(key_value: str, _key_meta: dict | None) -> dict:
    if not valid_token(key_value):
        msg = "The bot token does not have the shape Telegram issues."
        raise ValueError(msg)
    try:
        info = await verify_bot(key_value)
    except TelegramError as exc:
        msg = f"Telegram refused the bot token: {exc.description}."
        raise ValueError(msg) from exc
    return {"message": f"Bot @{info.username} verified."}


API_KEY_TESTERS = {
    APIProvider.VIEWDNS: _test_viewdns,
    APIProvider.HACKERONE: _test_hackerone,
    APIProvider.INTIGRITI: _test_intigriti,
    APIProvider.TELEGRAM: _test_telegram,
}


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


async def _rebind(session: AsyncSession, provider: APIProvider) -> None:
    channel = PROVIDER_CHANNELS.get(provider)
    if channel is not None:
        await ChannelService(session, channel).rebind()


def get_api_key_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> APIKeyService:
    return APIKeyService(session)


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    providers = await service.list_providers()
    return [
        p.model_copy(update={"testable": p.provider in API_KEY_TESTERS})
        for p in providers
    ]


@router.get("", response_model=list[APIKeyRead])
async def list_api_keys(
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    return await service.list_keys()


@router.post("", response_model=APIKeyRead, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreate,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    created = await service.create_key(data)
    await _rebind(service.session, data.provider)
    return created


@router.patch("/{key_id}", response_model=APIKeyRead)
async def update_api_key(
    key_id: str,
    data: APIKeyUpdate,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    updated = await service.update_key(key_id, data)
    if data.key_value is not None or data.is_enabled:
        await _rebind(service.session, updated.provider)
    return updated


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    api_key = await service._get_key_or_404(key_id)
    provider = api_key.provider
    await service.delete_key(key_id)
    channel = PROVIDER_CHANNELS.get(provider)
    if channel is not None:
        await ChannelService(service.session, channel).disconnect(None, keep_key=True)


def _plain(api_key: APIKey) -> str:
    name = API_PROVIDER_META[api_key.provider]["name"]
    return decrypt_stored(api_key.key_value, label=f"The {name} API key")


@router.get("/{key_id}/reveal")
async def reveal_api_key(
    key_id: str,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    response: Response,
):
    api_key = await service._get_key_or_404(key_id)
    response.headers["Cache-Control"] = "no-store"
    return {"key_value": _plain(api_key)}


@router.post("/{key_id}/test")
async def test_api_key(
    key_id: str,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    api_key = await service._get_key_or_404(key_id)

    tester = API_KEY_TESTERS.get(api_key.provider)
    if not tester:
        return {
            "provider": api_key.provider,
            "success": False,
            "message": f"No key test for {api_key.provider.value}.",
        }

    key_value = _plain(api_key)
    try:
        result = await tester(key_value, api_key.key_meta)
    except Exception as e:
        message = str(e).replace(key_value, MASK) if key_value else str(e)
        await service.record_test(api_key, False, message)
        return {"provider": api_key.provider, "success": False, "message": message}
    await service.record_test(api_key, True, result.get("message", ""))
    return {"provider": api_key.provider, "success": True, **result}
