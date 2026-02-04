from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.models import (
    Organization,
    OrganizationSummary,
    Project,
    TagSummary,
    Target,
    TargetBulkCreate,
    TargetBulkCreateResponse,
    TargetCreate,
    TargetImportResult,
    TargetRead,
    TargetType,
    TargetUpdate,
    TargetValidationRequest,
    TargetValidationResponse,
)
from app.services import get_or_create_organization, get_or_create_tag
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


@router.get("/counts", response_model=dict[str, int])
async def get_target_counts(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[str, Query(description="Filter by project slug")],
):
    """
    This endpoint serves as suimmary like count for dashboard and other ui elements.
    """
    # TODO: Check if project_id can be set null to find sumamry across all in case needed
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()
    if not project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await session.execute(
        select(Target.target_type, func.count(Target.id))
        .where(Target.project_id == project_id)
        .group_by(Target.target_type)
    )

    counts = {
        "all": 0,
        "domain": 0,
        "ip": 0,
        "ip_range": 0,
        "asn": 0,
        "url": 0,
    }

    for target_type, count in result.all():
        counts[target_type.value] = count
        counts["all"] += count

    return counts


@router.get("", response_model=Page[TargetRead])
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

    result = await paginate(session, query)

    result.items = [
        TargetRead(
            **target.model_dump(exclude={"organizations", "tags"}),
            organizations=[
                OrganizationSummary(
                    id=org.id,
                    name=org.name,
                    slug=org.slug,
                )
                for org in target.organizations
            ],
            tags=[
                TagSummary(
                    id=tag.id,
                    name=tag.name,
                    slug=tag.slug,
                    color=tag.color,
                )
                for tag in target.tags
            ],
        )
        for target in result.items
    ]

    return result


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
    for org_name in target_in.organization_names:
        org = await get_or_create_organization(
            org_name, project.id, current_user.id, session
        )
        organizations.append(org)

    tags = []
    for tag_name in target_in.tag_names:
        tag = await get_or_create_tag(tag_name, project.id, current_user.id, session)
        tags.append(tag)

    target = Target(
        target_value=target_in.target_value,
        target_type=target_type,
        display_name=target_in.display_name or target_in.target_value,
        project_id=project.id,
        created_by=current_user.id,
        organizations=organizations,
        tags=tags,
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)

    return TargetRead(
        **target.model_dump(exclude={"organizations", "tags"}),
        organizations=[
            OrganizationSummary(
                id=org.id,
                name=org.name,
                slug=org.slug,
            )
            for org in target.organizations
        ],
        tags=[
            TagSummary(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                color=tag.color,
            )
            for tag in target.tags
        ],
    )


@router.post(
    "/bulk",
    response_model=TargetBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_targets(
    bulk_in: TargetBulkCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Bulk import multiple targets into a project.

    All targets in the batch will receive the same tags and organizations. individual target tags/orgs are not supported.
    Invalid targets are skipped and reported in the response.
    Duplicate targets (within batch or already in project) are skipped.
    """
    project_result = await session.execute(
        select(Project).where(Project.slug == bulk_in.project_slug)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    existing_targets_result = await session.execute(
        select(Target.target_value).where(Target.project_id == project.id)
    )
    existing_target_values = set(existing_targets_result.scalars().all())
    organizations = []
    for org_name in bulk_in.organization_names:
        org = await get_or_create_organization(
            org_name, project.id, current_user.id, session
        )
        organizations.append(org)

    tags = []
    for tag_name in bulk_in.tag_names:
        tag = await get_or_create_tag(tag_name, project.id, current_user.id, session)
        tags.append(tag)

    results: list[TargetImportResult] = []
    imported_count = 0
    failed_count = 0
    skipped_duplicates = 0
    seen_in_batch: set[str] = set()

    for target_value in bulk_in.targets:
        _target_value = target_value.strip()

        # skip empty values
        if not _target_value:
            results.append(
                TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Empty target value",
                )
            )
            failed_count += 1
            continue

        # check dups in current batch
        if _target_value in seen_in_batch:
            results.append(
                TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Duplicate within import batch",
                )
            )
            skipped_duplicates += 1
            continue

        # check dups in existing project targets
        if _target_value in existing_target_values:
            results.append(
                TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Target already exists in project",
                )
            )
            skipped_duplicates += 1
            continue

        # validate target format
        target_type = validate_target(_target_value)
        if not target_type:
            results.append(
                TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Invalid target format",
                )
            )
            failed_count += 1
            continue

        # create the target
        target = Target(
            target_value=_target_value,
            target_type=target_type,
            display_name=_target_value,
            project_id=project.id,
            created_by=current_user.id,
            organizations=organizations,
            tags=tags,
        )
        session.add(target)

        # track for batch duplicate detection
        seen_in_batch.add(_target_value)
        existing_target_values.add(_target_value)

        results.append(
            TargetImportResult(
                target_value=_target_value,
                success=True,
                target_type=target_type,
                target_id=target.id,
            )
        )
        imported_count += 1

    await session.commit()

    return TargetBulkCreateResponse(
        total=len(bulk_in.targets),
        imported=imported_count,
        failed=failed_count,
        skipped_duplicates=skipped_duplicates,
        results=results,
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
        **target.model_dump(exclude={"organizations", "tags"}),
        organizations=[
            OrganizationSummary(
                id=org.id,
                name=org.name,
                slug=org.slug,
            )
            for org in target.organizations
        ],
        tags=[
            TagSummary(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                color=tag.color,
            )
            for tag in target.tags
        ],
    )


@router.patch("/{target_id}", response_model=TargetRead)
async def update_target(
    target_id: str,
    target_in: TargetUpdate,
    current_user: CurrentUser,
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

    if target_in.organization_names is not None:
        organizations = []
        for org_name in target_in.organization_names:
            org = await get_or_create_organization(
                org_name, target.project_id, current_user.id, session
            )
            organizations.append(org)
        target.organizations = organizations

    if target_in.tag_names is not None:
        tags = []
        for tag_name in target_in.tag_names:
            tag = await get_or_create_tag(
                tag_name, target.project_id, current_user.id, session
            )
            tags.append(tag)
        target.tags = tags

    target.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()
    await session.refresh(target)

    return TargetRead(
        **target.model_dump(exclude={"organizations", "tags"}),
        organizations=[
            OrganizationSummary(
                id=org.id,
                name=org.name,
                slug=org.slug,
            )
            for org in target.organizations
        ],
        tags=[
            TagSummary(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                color=tag.color,
            )
            for tag in target.tags
        ],
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

    await session.delete(target)
    await session.commit()
