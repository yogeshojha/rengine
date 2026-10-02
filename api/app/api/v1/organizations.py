import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.target_labels import (
    get_label,
    refuse_if_in_use,
    rename,
    target_counts,
)
from shared.definitions.tripwires import ScopeKind
from shared.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from shared.models.project import Project
from shared.models.target import TargetOrganization
from shared.utils.slug import add_with_unique_slug


def _read(org: Organization, counts: dict[uuid.UUID, int]) -> OrganizationRead:
    return OrganizationRead.model_validate(org).model_copy(
        update={"target_count": counts.get(org.id, 0)}
    )


router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[str, Query(description="Project slug")],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()
    if not project_id:
        return []

    result = await session.execute(
        select(Organization)
        .where(Organization.project_id == project_id)
        .order_by(Organization.name)
    )
    orgs = result.scalars().all()
    counts = await target_counts(
        session, TargetOrganization.organization_id, [o.id for o in orgs]
    )
    return [_read(o, counts) for o in orgs]


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

    existing_org = await session.execute(
        select(Organization).where(
            Organization.name == normalized_name,
            Organization.project_id == project.id,
        )
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this name exists in this project",
        )

    organization = Organization(
        name=normalized_name,
        description=organization_in.description,
        project_id=project.id,
        created_by=current_user.id,
    )
    try:
        await add_with_unique_slug(
            session, organization, normalized_name, project_id=project.id
        )
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this name exists in this project",
        ) from e
    await session.refresh(organization)
    return organization


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: uuid.UUID,
    organization_in: OrganizationUpdate,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    org = await get_label(session, Organization, organization_id, "Organization")
    if organization_in.name is not None:
        await rename(session, org, organization_in.name, "Organization")
    if "description" in organization_in.model_fields_set:
        org.description = organization_in.description
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this name exists in this project",
        ) from e
    counts = await target_counts(session, TargetOrganization.organization_id, [org.id])
    return _read(org, counts)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: uuid.UUID,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    org = await get_label(session, Organization, organization_id, "Organization")
    await refuse_if_in_use(session, org, ScopeKind.ORGANIZATION)
    await session.delete(org)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
