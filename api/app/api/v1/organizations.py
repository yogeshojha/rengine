from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from shared.models.project import Project
from shared.utils.slug import generate_slug

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


async def generate_unique_slug(
    name: str, project_id: str, session: AsyncSession
) -> str:
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 1

    while True:
        result = await session.execute(
            select(Organization).where(
                Organization.slug == slug, Organization.project_id == project_id
            )
        )
        if not result.scalar_one_or_none():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[
        str | None, Query(description="Filter by project slug")
    ] = None,
):
    query = select(Organization)

    if project_slug:
        project_result = await session.execute(
            select(Project.id).where(Project.slug == project_slug)
        )
        project_id = project_result.scalar_one_or_none()
        if project_id:
            query = query.where(Organization.project_id == project_id)
        else:
            return []

    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_in: OrganizationCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project).where(Project.slug == organization_in.project_slug)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    normalized_name = organization_in.name.strip().lower()

    # if organization with same name already exists in this project
    # one organization per name per project, however it can exist across projects
    existing_org = await session.execute(
        select(Organization).where(
            Organization.name == normalized_name,
            Organization.project_id == project.id,
        )
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization with this name already exists in this project",
        )

    slug = generate_slug(normalized_name)

    organization = Organization(
        name=normalized_name,
        slug=slug,
        project_id=project.id,
        created_by=current_user.id,
    )
    session.add(organization)
    await session.commit()
    await session.refresh(organization)
    return organization


@router.get("/{project_slug}/{slug}", response_model=OrganizationRead)
async def get_organization(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()

    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await session.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.project_id == project_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    return organization


@router.patch("/{project_slug}/{slug}", response_model=OrganizationRead)
async def update_organization(
    project_slug: str,
    slug: str,
    organization_in: OrganizationUpdate,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()

    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await session.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.project_id == project_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    update_data = organization_in.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_slug = await generate_unique_slug(update_data["name"], project_id, session)
        organization.slug = new_slug

    for field, value in update_data.items():
        setattr(organization, field, value)

    await session.commit()
    await session.refresh(organization)
    return organization


@router.delete("/{project_slug}/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()

    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await session.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.project_id == project_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    await session.delete(organization)
    await session.commit()
