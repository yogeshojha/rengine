from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.models.organization import Organization
from app.models.project import Project
from app.models.target import (
    Target,
    TargetCreate,
    TargetRead,
    TargetType,
    TargetUpdate,
    TargetValidationRequest,
    TargetValidationResponse,
)
from app.utils.validation import validate_target

router = APIRouter(
    prefix="/targets",
    tags=["targets"],
)


@router.post("/validate", response_model=TargetValidationResponse)
async def validate_target_endpoint(
    request: TargetValidationRequest,
    _current_user: CurrentUser,
):
    """
    This endpoint validates the format of a target value and determines its type.
    It does not store the target; it only checks if the format is valid.
    """
    target_type = validate_target(request.target_value)

    if target_type:
        return TargetValidationResponse(
            valid=True,
            target_type=target_type,
            error=None,
        )

    return TargetValidationResponse(
        valid=False,
        target_type=None,
        error="Invalid target format. Accepted formats: domain/subdomain, IP, IP range (CIDR), ASN (AS followed by numbers), or URL",
    )


@router.get("", response_model=list[TargetRead])
async def list_targets(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[
        str | None, Query(description="Filter by project slug")
    ] = None,
    organization_slug: Annotated[
        str | None, Query(description="Filter by organization slug")
    ] = None,
    target_type: Annotated[
        TargetType | None, Query(description="Filter by target type")
    ] = None,
):
    query = select(Target)

    if project_slug:
        project_result = await session.execute(
            select(Project.id).where(Project.slug == project_slug)
        )
        project_id = project_result.scalar_one_or_none()
        if project_id:
            query = query.where(Target.project_id == project_id)
        else:
            return []

    if organization_slug:
        org_result = await session.execute(
            select(Organization.id).where(Organization.slug == organization_slug)
        )
        org_id = org_result.scalar_one_or_none()
        if org_id:
            query = query.join(Target.organizations).where(Organization.id == org_id)
        else:
            return []

    if target_type:
        query = query.where(Target.target_type == target_type)

    result = await session.execute(query)
    targets = result.scalars().all()

    return [
        TargetRead(
            **target.model_dump(),
            organization_ids=[org.id for org in target.organizations],
        )
        for target in targets
    ]


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
async def create_target(
    target_in: TargetCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    target_type = validate_target(target_in.target_value)
    if not target_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target format",
        )

    project_result = await session.execute(
        select(Project).where(Project.slug == target_in.project_slug)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    existing_target = await session.execute(
        select(Target).where(
            Target.target_value == target_in.target_value,
            Target.project_id == project.id,
        )
    )
    if existing_target.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target already exists in this project",
        )

    organizations = []
    if target_in.organization_slugs:
        org_result = await session.execute(
            select(Organization).where(
                Organization.slug.in_(target_in.organization_slugs),
                Organization.project_id == project.id,
            )
        )
        organizations = list(org_result.scalars().all())

        if len(organizations) != len(target_in.organization_slugs):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more organizations not found in this project",
            )

    target = Target(
        target_value=target_in.target_value,
        target_type=target_type,
        display_name=target_in.display_name or target_in.target_value,
        project_id=project.id,
        created_by=current_user.id,
        organizations=organizations,
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)

    return TargetRead(
        **target.model_dump(),
        organization_ids=[org.id for org in target.organizations],
    )


@router.get("/{target_id}", response_model=TargetRead)
async def get_target(
    target_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )

    return TargetRead(
        **target.model_dump(),
        organization_ids=[org.id for org in target.organizations],
    )


@router.patch("/{target_id}", response_model=TargetRead)
async def update_target(
    target_id: str,
    target_in: TargetUpdate,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )

    if target_in.display_name is not None:
        target.display_name = target_in.display_name

    if target_in.organization_slugs is not None:
        org_result = await session.execute(
            select(Organization).where(
                Organization.slug.in_(target_in.organization_slugs),
                Organization.project_id == target.project_id,
            )
        )
        organizations = list(org_result.scalars().all())

        if len(organizations) != len(target_in.organization_slugs):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more organizations not found in this project",
            )

        target.organizations = organizations

    target.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()
    await session.refresh(target)

    return TargetRead(
        **target.model_dump(),
        organization_ids=[org.id for org in target.organizations],
    )


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )

    target.is_active = False
    await session.commit()
