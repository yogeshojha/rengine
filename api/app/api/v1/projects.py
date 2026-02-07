from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from shared.models.organization import Organization
from shared.models.project import Project, ProjectCreate, ProjectRead, ProjectSummary
from shared.models.tag import Tag
from shared.models.target import Target
from shared.utils.slug import generate_slug

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


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_inactive: bool = Query(False, description="Include soft-deleted projects"),
):
    query = select(Project)

    if not include_inactive:
        query = query.where(Project.is_active)

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{slug}/summary", response_model=ProjectSummary)
async def get_project_summary(
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(select(Project).where(Project.slug == slug))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    target_count_result = await session.execute(
        select(func.count(Target.id)).where(Target.project_id == project.id)
    )
    org_count_result = await session.execute(
        select(func.count(Organization.id)).where(Organization.project_id == project.id)
    )
    tag_count_result = await session.execute(
        select(func.count(Tag.id)).where(Tag.project_id == project.id)
    )
    return ProjectSummary(
        project=project,
        stats={
            "targets": target_count_result.scalar_one(),
            "organizations": org_count_result.scalar_one(),
            "tags": tag_count_result.scalar_one(),
        },
    )


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
