from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.models.project import Project, ProjectCreate, ProjectRead
from app.utils.slug import generate_slug

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


async def generate_unique_slug(name: str, session: AsyncSession) -> str:
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 1

    while True:
        result = await session.execute(select(Project).where(Project.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"


@router.get("", response_model=Page[ProjectRead])
async def list_projects(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_inactive: bool = Query(False, description="Include Deactivated projects"),
):
    query = select(Project)

    if not include_inactive:
        query = query.where(Project.is_active)

    return await paginate(session, query)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    slug = await generate_unique_slug(project_in.name, session)

    project = Project(
        name=project_in.name,
        slug=slug,
        created_by=current_user.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{slug}", response_model=ProjectRead)
async def get_project(
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Project).where(Project.slug == slug))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return project


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Project).where(Project.slug == slug))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    project.is_active = False
    await session.commit()
