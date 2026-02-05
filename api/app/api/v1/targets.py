from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.models import (
    TargetBulkCreate,
    TargetBulkCreateResponse,
    TargetCreate,
    TargetRead,
    TargetType,
    TargetUpdate,
    TargetValidationRequest,
    TargetValidationResponse,
)
from shared.services.target import TargetService

router = APIRouter(
    prefix="/targets",
    tags=["targets"],
)


def get_target_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TargetService:
    return TargetService(session)


@router.post("/validate", response_model=TargetValidationResponse)
async def validate_target_endpoint(
    request: TargetValidationRequest,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    target_type = await service.validate_target_value(request.target_value)

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
    service: Annotated[TargetService, Depends(get_target_service)],
    project_slug: Annotated[str, Query(description="Filter by project slug")],
):
    return await service.get_target_counts(project_slug)


@router.get("", response_model=Page[TargetRead])
async def list_targets(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[TargetService, Depends(get_target_service)],
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
    query = await service.list_targets(
        project_slug=project_slug,
        organization_slug=organization_slug,
        target_type=target_type,
    )

    result = await paginate(session, query)

    result.items = [service._to_target_read(target) for target in result.items]

    return result


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
async def create_target(
    target_in: TargetCreate,
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.create_target(target_in, current_user.id)


@router.post(
    "/bulk",
    response_model=TargetBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_targets(
    bulk_in: TargetBulkCreate,
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.bulk_create_targets(bulk_in, current_user.id)


@router.get("/{target_id}", response_model=TargetRead)
async def get_target(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.get_target(target_id)


@router.patch("/{target_id}", response_model=TargetRead)
async def update_target(
    target_id: str,
    target_in: TargetUpdate,
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.update_target(target_id, target_in, current_user.id)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    await service.delete_target(target_id)
