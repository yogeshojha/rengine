import asyncio
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret, try_decrypt
from shared.definitions.mode_features import VALID_MODES, capabilities_for
from shared.enums.instance import AIProvider
from shared.http import get_async_client
from shared.models.instance_settings import (
    InstanceSettings,
    InstanceSettingsRead,
    InstanceSettingsUpdate,
)
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now
from shared.utils.net import validate_public_https_url

_SINGLETON_KEY = "instance"
_TEST_TIMEOUT = 10
_OPENAI_BASE = "https://api.openai.com"
_ANTHROPIC_BASE = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"
_ANTHROPIC_PING_MODEL = "claude-haiku-4-5"
_GOOGLE_BASE = "https://generativelanguage.googleapis.com"
_HTTP_OK = 200
_HTTP_UNAUTHORIZED = 401
_VALID_AI_PROVIDERS = frozenset(p.value for p in AIProvider)


def _mask_ai_key(key: str) -> str:
    if len(key) <= 4:  # noqa: PLR2004
        return MASK
    return f"{MASK}{key[-4:]}"


def _validate_public_https_url(raw: str) -> str:
    validate_public_https_url(raw, label="Azure endpoint")
    return raw


class InstanceSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self) -> InstanceSettings:
        result = await self.session.execute(
            select(InstanceSettings).where(
                InstanceSettings.singleton_key == _SINGLETON_KEY
            )
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = InstanceSettings(singleton_key=_SINGLETON_KEY)
            self.session.add(settings)
            try:
                await self.session.commit()
                await self.session.refresh(settings)
            except IntegrityError:
                await self.session.rollback()
                result = await self.session.execute(
                    select(InstanceSettings).where(
                        InstanceSettings.singleton_key == _SINGLETON_KEY
                    )
                )
                settings = result.scalar_one()
        return settings

    def to_read(self, settings: InstanceSettings) -> InstanceSettingsRead:
        key = try_decrypt(settings.ai_api_key_encrypted)
        return InstanceSettingsRead(
            id=settings.id,
            singleton_key=settings.singleton_key,
            instance_name=settings.instance_name,
            timezone=settings.timezone,
            mode=settings.mode,
            onboarding_completed=settings.onboarding_completed,
            onboarding_completed_at=settings.onboarding_completed_at,
            onboarding_completed_by=settings.onboarding_completed_by,
            onboarding_step=settings.onboarding_step,
            onboarding_state=settings.onboarding_state or {},
            scan_history_retention_days=settings.scan_history_retention_days,
            screenshot_retention_days=settings.screenshot_retention_days,
            ai_enabled=settings.ai_enabled,
            ai_provider=settings.ai_provider,
            ai_model=settings.ai_model,
            ai_api_key_masked=_mask_ai_key(key) if key else None,
            ai_configured=bool(settings.ai_api_key_encrypted),
            ai_features=settings.ai_features or {},
            capabilities=capabilities_for(settings.mode),
            created_at=settings.created_at,
            updated_at=settings.updated_at,
        )

    async def update(self, data: InstanceSettingsUpdate) -> InstanceSettingsRead:
        settings = await self.get_or_create()

        if data.instance_name is not None:
            settings.instance_name = data.instance_name
        if data.timezone is not None:
            try:
                ZoneInfo(data.timezone)
            except Exception as exc:
                msg = f"Invalid timezone '{data.timezone}'."
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=msg
                ) from exc
            settings.timezone = data.timezone
        if data.mode is not None:
            if data.mode not in VALID_MODES:
                msg = f"Invalid mode '{data.mode}'. Must be one of {', '.join(sorted(VALID_MODES))}."
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
            settings.mode = data.mode
        if data.scan_history_retention_days is not None:
            settings.scan_history_retention_days = data.scan_history_retention_days
        if data.screenshot_retention_days is not None:
            settings.screenshot_retention_days = data.screenshot_retention_days
        if data.ai_enabled is not None:
            settings.ai_enabled = data.ai_enabled
        if data.ai_provider is not None:
            if data.ai_provider not in _VALID_AI_PROVIDERS:
                msg = (
                    f"Invalid ai_provider '{data.ai_provider}'. "
                    f"Must be one of {', '.join(sorted(_VALID_AI_PROVIDERS))}."
                )
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
            settings.ai_provider = data.ai_provider
        if data.ai_model is not None:
            settings.ai_model = data.ai_model
        if data.ai_features is not None:
            settings.ai_features = dict(data.ai_features)

        if data.ai_api_key is not None and data.ai_api_key != MASK:
            settings.ai_api_key_encrypted = (
                encrypt_secret(data.ai_api_key) if data.ai_api_key else None
            )

        settings.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(settings)
        return self.to_read(settings)

    async def test_ai(
        self, provider: str, model: str | None, api_key: str | None
    ) -> dict:
        if not api_key or api_key == MASK:
            api_key = try_decrypt((await self.get_or_create()).ai_api_key_encrypted)
        if not api_key:
            return {"success": False, "message": "No API key provided."}

        try:
            return await self._ping(provider, model, api_key)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            return {"success": False, "message": f"Connection failed: {exc}"}

    async def _ping(self, provider: str, model: str | None, api_key: str) -> dict:
        async with get_async_client(timeout=_TEST_TIMEOUT) as client:
            if provider == AIProvider.OPENAI.value:
                return await self._ping_openai(client, api_key)
            if provider == AIProvider.ANTHROPIC.value:
                return await self._ping_anthropic(client, api_key)
            if provider == AIProvider.GOOGLE.value:
                return await self._ping_google(client, api_key)
            if provider == AIProvider.AZURE_OPENAI.value:
                return await self._ping_azure(client, model, api_key)
        return {"success": False, "message": f"Unsupported provider '{provider}'."}

    async def _ping_openai(self, client: httpx.AsyncClient, api_key: str) -> dict:
        resp = await client.get(
            f"{_OPENAI_BASE}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return self._result(resp, "OpenAI")

    async def _ping_anthropic(self, client: httpx.AsyncClient, api_key: str) -> dict:
        resp = await client.post(
            f"{_ANTHROPIC_BASE}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
            json={
                "model": _ANTHROPIC_PING_MODEL,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
        return self._result(resp, "Anthropic")

    async def _ping_google(self, client: httpx.AsyncClient, api_key: str) -> dict:
        resp = await client.get(
            f"{_GOOGLE_BASE}/v1beta/models",
            params={"key": api_key},
        )
        return self._result(resp, "Google")

    async def _ping_azure(
        self, client: httpx.AsyncClient, model: str | None, api_key: str
    ) -> dict:
        if not model:
            return {
                "success": False,
                "message": "Azure OpenAI requires an endpoint URL in the model field.",
            }
        url = await asyncio.to_thread(_validate_public_https_url, model.rstrip("/"))
        resp = await client.get(
            url,
            headers={"api-key": api_key},
            follow_redirects=False,
        )
        ok = resp.status_code != _HTTP_UNAUTHORIZED
        if ok:
            return {"success": True, "message": "Azure OpenAI reachable."}
        return {"success": False, "message": "Azure OpenAI authentication failed."}

    def _result(self, resp: httpx.Response, name: str) -> dict:
        if resp.status_code == _HTTP_OK:
            return {"success": True, "message": f"{name} connection successful."}
        if resp.status_code == _HTTP_UNAUTHORIZED:
            return {"success": False, "message": f"{name} authentication failed."}
        return {
            "success": False,
            "message": f"{name} returned status {resp.status_code}.",
        }
