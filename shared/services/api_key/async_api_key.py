from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from shared.definitions.api_keys import API_PROVIDER_META, PROVIDER_GROUP_LABELS
from shared.definitions.mode_features import provider_allowed
from shared.enums.api_key import APIProvider
from shared.enums.instance import InstanceMode
from shared.models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyRead,
    APIKeyUpdate,
    ProviderInfo,
)
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.services.api_key.sync_api_key import open_key
from shared.services.scan_resolve import mask_tail
from shared.utils.crypto import encrypt_secret, try_decrypt
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from fastapi import HTTPException


def _http_error(status: HTTPStatus, detail: str) -> HTTPException:
    from fastapi import HTTPException  # noqa: PLC0415

    return HTTPException(status_code=status, detail=detail)


class APIKeyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _instance_mode(self) -> str:
        result = await self.session.execute(
            select(InstanceSettings.mode).where(
                InstanceSettings.singleton_key == SINGLETON_KEY
            )
        )
        return result.scalar_one_or_none() or InstanceMode.BUG_BOUNTY.value

    def _to_read(self, api_key: APIKey) -> APIKeyRead:
        return APIKeyRead(
            id=api_key.id,
            provider=api_key.provider,
            key_value_masked=mask_tail(try_decrypt(api_key.key_value) or ""),
            key_meta=api_key.key_meta,
            is_enabled=api_key.is_enabled,
            last_test_at=api_key.last_test_at,
            last_test_ok=api_key.last_test_ok,
            last_test_message=api_key.last_test_message,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
        )

    async def list_keys(self) -> list[APIKeyRead]:
        result = await self.session.execute(select(APIKey).order_by(APIKey.provider))
        return [self._to_read(k) for k in result.scalars().all()]

    async def list_providers(self) -> list[ProviderInfo]:
        result = await self.session.execute(select(APIKey))
        configured = {k.provider: k for k in result.scalars().all()}

        providers = []
        for provider, meta in API_PROVIDER_META.items():
            key = configured.get(provider)
            providers.append(
                ProviderInfo(
                    provider=provider,
                    name=meta["name"],
                    description=meta["description"],
                    docs_url=meta["docs_url"],
                    icon=meta.get("icon", "package"),
                    requires_username=meta.get("requires_username", False),
                    group=meta["group"],
                    group_label=PROVIDER_GROUP_LABELS[meta["group"]],
                    configured=key is not None,
                    is_enabled=key.is_enabled if key else False,
                )
            )
        mode = await self._instance_mode()
        return [p for p in providers if provider_allowed(mode, p.provider.value)]

    async def create_key(self, data: APIKeyCreate) -> APIKeyRead:
        name = API_PROVIDER_META[data.provider]["name"]
        mode = await self._instance_mode()
        if not provider_allowed(mode, data.provider.value):
            raise _http_error(
                HTTPStatus.FORBIDDEN,
                f"{name} requires bug bounty mode.",
            )

        if API_PROVIDER_META.get(data.provider, {}).get("requires_username"):
            username = (data.key_meta or {}).get("username")
            if not username or not str(username).strip():
                raise _http_error(
                    HTTPStatus.BAD_REQUEST,
                    f"{name} requires a username.",
                )

        existing = await self.session.execute(
            select(APIKey).where(
                APIKey.provider == data.provider,
            )
        )
        if existing.scalar_one_or_none():
            raise _http_error(
                HTTPStatus.CONFLICT,
                f"An API key for {name} exists.",
            )

        api_key = APIKey(
            provider=data.provider,
            key_value=encrypt_secret(data.key_value),
            key_meta=data.key_meta,
        )
        self.session.add(api_key)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise _http_error(
                HTTPStatus.CONFLICT,
                f"An API key for {name} exists.",
            ) from e
        await self.session.refresh(api_key)
        return self._to_read(api_key)

    async def update_key(self, key_id: str, data: APIKeyUpdate) -> APIKeyRead:
        api_key = await self._get_key_or_404(key_id)

        if data.key_value is not None:
            api_key.key_value = encrypt_secret(data.key_value)
            api_key.last_test_at = None
            api_key.last_test_ok = None
            api_key.last_test_message = None
        if data.is_enabled is not None:
            api_key.is_enabled = data.is_enabled
        if data.key_meta is not None:
            api_key.key_meta = data.key_meta

        api_key.updated_at = utc_now()
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return self._to_read(api_key)

    async def record_test(self, api_key: APIKey, ok: bool, message: str) -> None:
        api_key.last_test_at = utc_now()
        api_key.last_test_ok = ok
        api_key.last_test_message = message[:500]
        self.session.add(api_key)
        await self.session.commit()

    async def delete_key(self, key_id: str) -> None:
        api_key = await self._get_key_or_404(key_id)
        await self.session.delete(api_key)
        await self.session.commit()

    async def get_key_for_provider(self, provider: APIProvider) -> str | None:
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.provider == provider,
                APIKey.is_enabled.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        return open_key(api_key)

    async def disable_key(self, provider: APIProvider) -> None:
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.provider == provider,
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.is_enabled = False
            api_key.updated_at = utc_now()
            self.session.add(api_key)
            await self.session.commit()

    async def _get_key_or_404(self, key_id: str) -> APIKey:
        try:
            uuid_id = uuid.UUID(key_id)
        except ValueError as e:
            raise _http_error(HTTPStatus.BAD_REQUEST, "Invalid key ID.") from e

        result = await self.session.execute(select(APIKey).where(APIKey.id == uuid_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise _http_error(HTTPStatus.NOT_FOUND, "API key not found.")
        return api_key
