from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser
from app.core.database import get_session
from app.services.proxy import ProxyService
from shared.models.proxy import (
    ProxyCreate,
    ProxyRead,
    ProxyTestResult,
    ProxyUpdate,
)

router = APIRouter(prefix="/proxies", tags=["proxies"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProxyService:
    return ProxyService(session)


@router.get("", response_model=list[ProxyRead])
async def list_proxies(
    _current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    return await service.list()


@router.post("", response_model=ProxyRead, status_code=status.HTTP_201_CREATED)
async def create_proxy(
    data: ProxyCreate,
    current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    return await service.create(data, created_by=current_user.id)


@router.get("/{id}", response_model=ProxyRead)
async def get_proxy(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    return await service.get(id)


@router.patch("/{id}", response_model=ProxyRead)
async def update_proxy(
    id: UUID,
    data: ProxyUpdate,
    _current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    return await service.update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    await service.delete(id)


@router.post("/{id}/test", response_model=ProxyTestResult)
async def test_proxy(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    return await service.test(id)


@router.post("/{id}/set-default", response_model=ProxyRead)
async def set_default_proxy(
    id: UUID,
    _current_user: CurrentSuperuser,
    service: Annotated[ProxyService, Depends(get_service)],
):
    return await service.set_default(id)
