from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser
from app.core.database import get_session
from shared.models.api_key import APIKeyCreate, APIKeyRead, APIKeyUpdate, ProviderInfo
from shared.services.api_key import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def get_api_key_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> APIKeyService:
    return APIKeyService(session)


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    return await service.list_providers()


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
    return await service.create_key(data)


@router.patch("/{key_id}", response_model=APIKeyRead)
async def update_api_key(
    key_id: str,
    data: APIKeyUpdate,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    return await service.update_key(key_id, data)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    await service.delete_key(key_id)


@router.get("/{key_id}/reveal")
async def reveal_api_key(
    key_id: str,
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    api_key = await service._get_key_or_404(key_id)
    return {"key_value": api_key.key_value}


@router.post("/{key_id}/test")
async def test_api_key(
    key_id: str,
    _current_user: CurrentSuperuser,  # noqa: PT019
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    api_key = await service._get_key_or_404(key_id)

    # TODO: implement per-provider test calls
    return {
        "provider": api_key.provider,
        "status": "not_implemented",
        "message": f"Test endpoint for {api_key.provider.value} not yet implemented",
    }
