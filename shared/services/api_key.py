import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from shared.enums.api_key import APIProvider
from shared.models.api_key import (
    API_PROVIDER_META,
    APIKey,
    APIKeyCreate,
    APIKeyRead,
    APIKeyUpdate,
    ProviderInfo,
)
from shared.utils.datetime import utc_now


class APIKeyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _mask_key(self, key_value: str) -> str:
        if len(key_value) <= 4:  # noqa: PLR2004
            return "****"
        return f"****{key_value[-4:]}"

    def _to_read(self, api_key: APIKey) -> APIKeyRead:
        return APIKeyRead(
            id=api_key.id,
            provider=api_key.provider,
            key_value_masked=self._mask_key(api_key.key_value),
            is_enabled=api_key.is_enabled,
            usage_counter=api_key.usage_counter,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            meta=API_PROVIDER_META.get(api_key.provider, {}),
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
                    configured=key is not None,
                    is_enabled=key.is_enabled if key else False,
                )
            )
        return providers

    async def create_key(self, data: APIKeyCreate) -> APIKeyRead:
        existing = await self.session.execute(
            select(APIKey).where(
                APIKey.provider == data.provider,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"API key for {data.provider.value} already exists in this project",
            )

        api_key = APIKey(
            provider=data.provider,
            key_value=data.key_value,
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return self._to_read(api_key)

    async def update_key(self, key_id: str, data: APIKeyUpdate) -> APIKeyRead:
        api_key = await self._get_key_or_404(key_id)

        if data.key_value is not None:
            api_key.key_value = data.key_value
        if data.is_enabled is not None:
            api_key.is_enabled = data.is_enabled

        api_key.updated_at = utc_now()
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return self._to_read(api_key)

    async def delete_key(self, key_id: str) -> None:
        api_key = await self._get_key_or_404(key_id)
        await self.session.delete(api_key)
        await self.session.commit()

    async def get_key_for_provider(self, provider: APIProvider) -> str | None:
        """Get the raw key value for a provider. Used by other services/workers."""
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.provider == provider,
                APIKey.is_enabled == True,  # noqa: E712
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        return api_key.key_value

    async def increment_usage(self, provider: APIProvider) -> None:
        """Increment usage counter after a successful API call."""
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.provider == provider,
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.usage_counter += 1
            api_key.last_used_at = utc_now()
            self.session.add(api_key)
            await self.session.commit()

    async def disable_key(self, provider: APIProvider) -> None:
        """we can disable a key when the provider returns a rate limit or quota exhausted error."""
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid key ID format",
            ) from e

        result = await self.session.execute(select(APIKey).where(APIKey.id == uuid_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )
        return api_key
