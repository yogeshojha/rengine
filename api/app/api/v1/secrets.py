from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import SecretScope
from app.core.database import get_session
from app.services.secret import SecretService
from shared.models.asset_query import QueryGroups
from shared.models.secret import (
    SecretCoverageRead,
    SecretDetail,
    SecretFacets,
    SecretFilter,
    SecretPage,
)
from shared.services.asset_query import lead_cache

router = APIRouter(prefix="/secrets", tags=["secrets"])

MAX_COUNT_QUERIES = 25


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SecretService:
    return SecretService(session)


@router.post("/search", response_model=SecretPage)
async def search_secrets(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scope: SecretScope,
    body: SecretFilter,
):
    return await lead_cache.cached(
        service.session,
        name="search:secrets",
        scans=scope.ids,
        facets=body.model_dump_json(),
        model=SecretPage,
        build=lambda: service.search(scope, body),
        keep=lambda page: page.error is None,
    )


@router.get("/facets", response_model=SecretFacets)
async def secret_facets(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scope: SecretScope,
):
    return await service.facets(scope)


@router.get("/coverage", response_model=SecretCoverageRead)
async def secret_coverage(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scope: SecretScope,
):
    return await service.coverage(scope)


@router.post("/search/counts", response_model=dict[str, int])
async def secret_counts(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scope: SecretScope,
    queries: Annotated[list[str], Body(embed=True, max_length=MAX_COUNT_QUERIES)],
):
    return await service.counts(scope, queries)


@router.post("/search/groups", response_model=QueryGroups)
async def secret_groups(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scope: SecretScope,
    group_by: Annotated[str, Query(description="Group dimension key", max_length=40)],
    body: SecretFilter,
):
    return await service.groups(scope, body, group_by)


@router.get("/total", response_model=int)
async def secret_total(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    return await service.scan_total(scan_id)


@router.get("/{secret_id}", response_model=SecretDetail)
async def get_secret(
    _current_user: CurrentUser,
    service: Annotated[SecretService, Depends(get_service)],
    scope: SecretScope,
    secret_id: UUID,
):
    detail = await service.detail(scope, secret_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return detail
