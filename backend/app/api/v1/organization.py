from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.models import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    Project,
)
from app.utils.slug import generate_slug

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
    project_slug: str | None = Query(
        None, description="Filter by project slug"
    ),  # Changed
):
    query = select(Organization)

    if project_slug:
        result = await session.execute(
            select(Project.id).where(Project.slug == project_slug)
        )
        project_id = result.scalar_one_or_none()
        if project_id:
            query = query.where(Organization.project_id == project_id)
        else:
            # no matching projects means no org matching
            return []

    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_in: OrganizationCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Project).where(Project.slug == organization_in.project_slug)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    slug = await generate_unique_slug(organization_in.name, project.id, session)

    organization = Organization(
        name=organization_in.name,
        slug=slug,
        project_id=project.id,
        created_by=current_user.id,
    )
    session.add(organization)
    await session.commit()
    await session.refresh(organization)
    return organization


@router.get("/{slug}", response_model=OrganizationRead)
async def get_organization(
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Organization).where(Organization.slug == slug)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    return organization


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Organization).where(Organization.slug == slug)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    await session.delete(organization)
    await session.commit()
