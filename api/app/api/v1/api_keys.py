from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser
from app.core.database import get_session
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKeyCreate, APIKeyRead, APIKeyUpdate, ProviderInfo
from shared.services.api_key.async_api_key import APIKeyService
from tools.viewdns.client import ViewDNSClient


async def _test_viewdns(key_value: str) -> dict:
    client = ViewDNSClient(key_value)
    raw = await client.ip_history("rengine.wiki")
    record_count = len(raw.get("records", []))
    return {"message": f"OK — {record_count} IP history records for rengine.wiki"}


API_KEY_TESTERS = {
    APIProvider.VIEWDNS: _test_viewdns,
}


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
    _current_user: CurrentSuperuser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    api_key = await service._get_key_or_404(key_id)

    tester = API_KEY_TESTERS.get(api_key.provider)
    if not tester:
        return {
            "provider": api_key.provider,
            "success": False,
            "message": f"No test available for {api_key.provider.value}",
        }

    try:
        result = await tester(api_key.key_value)
        return {"provider": api_key.provider, "success": True, **result}
    except Exception as e:
        return {"provider": api_key.provider, "success": False, "message": str(e)}
