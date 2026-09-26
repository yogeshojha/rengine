from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.project import ProjectService
from shared.models.project import ProjectCreate, ProjectRead, ProjectSummary

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectService:
    return ProjectService(session)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    _current_user: CurrentUser,
    service: Annotated[ProjectService, Depends(get_service)],
    include_inactive: bool = Query(False, description="Include soft-deleted projects"),
):
    return await service.list(include_inactive=include_inactive)


@router.get("/{slug}/summary", response_model=ProjectSummary)
async def get_project_summary(
    slug: str,
    _current_user: CurrentUser,
    service: Annotated[ProjectService, Depends(get_service)],
):
    return await service.summary(slug)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentSuperuser,
    service: Annotated[ProjectService, Depends(get_service)],
):
    return await service.create(project_in, current_user.id)


@router.get("/{slug}", response_model=ProjectRead)
async def get_project(
    slug: str,
    _current_user: CurrentUser,
    service: Annotated[ProjectService, Depends(get_service)],
):
    return await service.get(slug)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    slug: str,
    _current_user: CurrentSuperuser,
    service: Annotated[ProjectService, Depends(get_service)],
):
    await service.deactivate(slug)
