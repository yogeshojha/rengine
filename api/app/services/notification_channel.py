from __future__ import annotations

import asyncio
import json
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret, try_decrypt
from shared.enums.notification_channel import NotificationProvider
from shared.models.notification_channel import (
    PROVIDERS,
    NotificationChannel,
    NotificationChannelCreate,
    NotificationChannelRead,
    NotificationChannelTestResult,
    NotificationChannelUpdate,
    NotificationPreference,
)
from shared.services.notifier import send_one
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now
from shared.utils.net import validate_public_https_url

_TOKEN_TAIL = 4

SECRET_FIELDS: dict[str, set[str]] = {
    NotificationProvider.SLACK.value: {"webhook_url"},
    NotificationProvider.DISCORD.value: {"webhook_url"},
    NotificationProvider.TEAMS.value: {"webhook_url"},
    NotificationProvider.WEBHOOK.value: {"webhook_url"},
    NotificationProvider.TELEGRAM.value: {"bot_token"},
    NotificationProvider.EMAIL.value: {"password"},
    NotificationProvider.CUSTOM.value: {"apprise_url"},
}

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    NotificationProvider.SLACK.value: ("webhook_url",),
    NotificationProvider.DISCORD.value: ("webhook_url",),
    NotificationProvider.TEAMS.value: ("webhook_url",),
    NotificationProvider.WEBHOOK.value: ("webhook_url",),
    NotificationProvider.TELEGRAM.value: ("bot_token", "chat_id"),
    NotificationProvider.EMAIL.value: ("smtp_host", "username", "password", "to_email"),
    NotificationProvider.CUSTOM.value: ("apprise_url",),
}

_URL_FIELDS = {"webhook_url", "apprise_url"}

_DISALLOWED_CUSTOM_SCHEMES = frozenset(
    {"http", "https", "json", "jsons", "xml", "xmls", "form", "forms"}
)

_DIRECT_POST_PROVIDERS = frozenset(
    {NotificationProvider.WEBHOOK.value, NotificationProvider.TEAMS.value}
)


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_public_https_url(raw: str) -> None:
    try:
        validate_public_https_url(raw, label="Webhook URL")
    except ValueError as exc:
        raise _bad(str(exc)) from exc


def _validate_config(provider: str, config: dict) -> None:
    for field in REQUIRED_FIELDS.get(provider, ()):
        value = config.get(field)
        if not isinstance(value, str | int) or (
            isinstance(value, str) and not value.strip()
        ):
            msg = f"{provider} config requires a non-empty '{field}'."
            raise _bad(msg)
    if provider == NotificationProvider.CUSTOM.value:
        scheme = urlsplit(str(config.get("apprise_url", ""))).scheme.lower()
        if scheme in _DISALLOWED_CUSTOM_SCHEMES:
            msg = (
                f"Apprise scheme '{scheme}://' is not allowed for custom channels. "
                "Use the 'Webhook' channel type for raw HTTP endpoints."
            )
            raise _bad(msg)
    if provider in _DIRECT_POST_PROVIDERS:
        _validate_public_https_url(str(config.get("webhook_url", "")))


def _mask_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or url[:24]
    if parts.port:
        host = f"{host}:{parts.port}"
    scheme = parts.scheme or "https"
    return f"{scheme}://{host}/{MASK}"


def _mask_value(value: str) -> str:
    return f"{MASK}{value[-_TOKEN_TAIL:]}" if len(value) >= _TOKEN_TAIL else MASK


def _mask_config(provider: str, config: dict) -> dict:
    secret = SECRET_FIELDS.get(provider, set())
    masked: dict = {}
    for key, value in (config or {}).items():
        if key in secret and isinstance(value, str):
            masked[key] = _mask_url(value) if key in _URL_FIELDS else _mask_value(value)
        else:
            masked[key] = value
    return masked


def _merge_config(provider: str, stored: dict, incoming: dict) -> dict:
    merged = dict(incoming)
    for field in SECRET_FIELDS.get(provider, set()):
        value = incoming.get(field)
        if value is None or value == "" or (isinstance(value, str) and MASK in value):
            if field in stored:
                merged[field] = stored[field]
            else:
                merged.pop(field, None)
    return merged


def _decrypt_config(channel: NotificationChannel) -> dict:
    raw = try_decrypt(channel.config_encrypted)
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _to_read(channel: NotificationChannel) -> NotificationChannelRead:
    config = _decrypt_config(channel)
    return NotificationChannelRead(
        id=channel.id,
        name=channel.name,
        provider=channel.provider,
        is_active=channel.is_active,
        config_masked=_mask_config(channel.provider, config),
        events=NotificationPreference(**(channel.events or {})),
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        last_test_at=channel.last_test_at,
        last_test_ok=channel.last_test_ok,
        last_test_message=channel.last_test_message,
    )


class NotificationChannelService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> list[NotificationChannelRead]:
        result = await self.session.execute(
            select(NotificationChannel).order_by(NotificationChannel.updated_at.desc())
        )
        return [_to_read(c) for c in result.scalars().all()]

    async def get(self, id: UUID) -> NotificationChannelRead:
        channel = await self._get_or_404(id)
        return _to_read(channel)

    async def create(
        self, data: NotificationChannelCreate, created_by: UUID
    ) -> NotificationChannelRead:
        if data.provider not in PROVIDERS:
            msg = f"Invalid provider. Must be one of {', '.join(PROVIDERS)}."
            raise _bad(msg)
        config = {k: v for k, v in (data.config or {}).items() if v is not None}
        _validate_config(data.provider, config)

        channel = NotificationChannel(
            name=data.name,
            provider=data.provider,
            is_active=data.is_active,
            config_encrypted=encrypt_secret(json.dumps(config)),
            events=data.events.model_dump(),
            created_by=created_by,
        )
        self.session.add(channel)
        await self.session.commit()
        await self.session.refresh(channel)
        return _to_read(channel)

    async def update(
        self, id: UUID, data: NotificationChannelUpdate
    ) -> NotificationChannelRead:
        channel = await self._get_or_404(id)

        if data.name is not None:
            channel.name = data.name
        if data.is_active is not None:
            channel.is_active = data.is_active
        if data.events is not None:
            channel.events = data.events.model_dump()
        if data.config is not None:
            stored = _decrypt_config(channel)
            incoming = {k: v for k, v in data.config.items() if v is not None}
            merged = _merge_config(channel.provider, stored, incoming)
            _validate_config(channel.provider, merged)
            channel.config_encrypted = encrypt_secret(json.dumps(merged))

        channel.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(channel)
        return _to_read(channel)

    async def delete(self, id: UUID) -> bool:
        channel = await self._get_or_404(id)
        await self.session.delete(channel)
        await self.session.commit()
        return True

    async def test_config(
        self, provider: str, config: dict
    ) -> NotificationChannelTestResult:
        if provider not in PROVIDERS:
            msg = f"Invalid provider. Must be one of {', '.join(PROVIDERS)}."
            raise _bad(msg)
        config = {k: v for k, v in (config or {}).items() if v is not None}
        _validate_config(provider, config)
        ok, message = await asyncio.to_thread(
            send_one,
            provider,
            config,
            "reNgine test notification",
            "✅ This is a test notification from reNgine. Channel is working.",
            "info",
        )
        return NotificationChannelTestResult(success=ok, message=message)

    async def test(self, id: UUID) -> NotificationChannelTestResult:
        channel = await self._get_or_404(id)
        config = _decrypt_config(channel)
        ok, message = await asyncio.to_thread(
            send_one,
            channel.provider,
            config,
            "reNgine test notification",
            "✅ This is a test notification from reNgine. Channel is working.",
            "info",
        )
        channel.last_test_at = utc_now()
        channel.last_test_ok = ok
        channel.last_test_message = message[:500]
        await self.session.commit()
        return NotificationChannelTestResult(success=ok, message=message)

    async def _get_or_404(self, id: UUID) -> NotificationChannel:
        result = await self.session.execute(
            select(NotificationChannel).where(NotificationChannel.id == id)
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification channel not found",
            )
        return channel
