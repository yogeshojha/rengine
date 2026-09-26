from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.organization import OrganizationService
from shared.models.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationService:
    return OrganizationService(session)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    _current_user: CurrentUser,
    service: Annotated[OrganizationService, Depends(get_service)],
    project_slug: Annotated[
        str | None, Query(description="Filter by project slug")
    ] = None,
):
    return await service.list(project_slug)


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_in: OrganizationCreate,
    current_user: CurrentUser,
    service: Annotated[OrganizationService, Depends(get_service)],
):
    return await service.create(organization_in, current_user.id)


@router.get("/{project_slug}/{slug}", response_model=OrganizationRead)
async def get_organization(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    service: Annotated[OrganizationService, Depends(get_service)],
):
    return await service.get(project_slug, slug)


@router.patch("/{project_slug}/{slug}", response_model=OrganizationRead)
async def update_organization(
    project_slug: str,
    slug: str,
    organization_in: OrganizationUpdate,
    _current_user: CurrentUser,
    service: Annotated[OrganizationService, Depends(get_service)],
):
    return await service.update(project_slug, slug, organization_in)


@router.delete("/{project_slug}/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    service: Annotated[OrganizationService, Depends(get_service)],
):
    await service.delete(project_slug, slug)
