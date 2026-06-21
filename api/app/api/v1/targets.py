from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.target import TargetService
from app.services.target_filters import SignalName, SortDir, SortKey
from shared.definitions.constants import MAX_TARGET_IMPORT
from shared.models import (
    TargetBulkCreate,
    TargetBulkCreateResponse,
    TargetCreate,
    TargetImportRequest,
    TargetRead,
    TargetType,
    TargetUpdate,
    TargetValidationRequest,
    TargetValidationResponse,
)
from shared.schemas.target_detail import (
    EnrichmentRefreshResponse,
    TargetBgpDetailResponse,
    TargetDetailRead,
    TargetDnsDetailResponse,
    TargetWhoisDetailResponse,
)

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
            target_value=request.target_value,
        )

    return TargetValidationResponse(
        valid=False,
        target_type=None,
        error="Invalid target format. Accepted formats: domain/subdomain, IP, IP range (CIDR), ASN (AS followed by numbers), or URL",
        target_value=request.target_value,
    )


@router.post("/validate/bulk", response_model=list[TargetValidationResponse])
async def validate_bulk_target(
    request: list[TargetValidationRequest],
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    if len(request) > MAX_TARGET_IMPORT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_TARGET_IMPORT} targets allowed per request",
        )

    seen = set()
    unique_requests = []
    for req in request:
        if req.target_value not in seen:
            seen.add(req.target_value)
            unique_requests.append(req)

    results = []
    for req in unique_requests:
        target_type = await service.validate_target_value(req.target_value)

        if target_type:
            results.append(
                TargetValidationResponse(
                    valid=True,
                    target_type=target_type,
                    error=None,
                    target_value=req.target_value,
                )
            )
        else:
            results.append(
                TargetValidationResponse(
                    valid=False,
                    target_type=None,
                    error="Invalid target format. Accepted formats: domain/subdomain, IP, IP range (CIDR), ASN (AS followed by numbers), or URL",
                    target_value=req.target_value,
                )
            )

    return results


@router.get("/counts", response_model=dict[str, int])
async def get_target_counts(
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
    project_slug: Annotated[str, Query(description="Filter by project slug")],
):
    return await service.get_target_counts(project_slug)


class TargetStatsResponse(BaseModel):
    total: int
    expiring: int
    attention: int
    awaiting: int
    enriched: int


@router.get("/stats", response_model=TargetStatsResponse)
async def get_target_stats(
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
    project_slug: Annotated[str, Query(description="Filter by project slug")],
    search: Annotated[str | None, Query(description="Search target value/name")] = None,
    organization_ids: Annotated[
        list[UUID] | None, Query(description="Filter by organization IDs")
    ] = None,
    tag_ids: Annotated[
        list[UUID] | None, Query(description="Filter by tag IDs")
    ] = None,
    target_type: Annotated[
        TargetType | None, Query(description="Filter by target type")
    ] = None,
):
    return await service.get_target_stats(
        project_slug=project_slug,
        search=search,
        organization_ids=organization_ids,
        tag_ids=tag_ids,
        target_type=target_type,
    )


@router.get("/ids", response_model=list[UUID])
async def list_matching_target_ids(
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
    project_slug: Annotated[str, Query(description="Filter by project slug")],
    search: Annotated[str | None, Query()] = None,
    organization_ids: Annotated[list[UUID] | None, Query()] = None,
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
    target_type: Annotated[TargetType | None, Query()] = None,
    signal: Annotated[SignalName | None, Query()] = None,
):
    return await service.get_matching_target_ids(
        project_slug=project_slug,
        search=search,
        organization_ids=organization_ids,
        tag_ids=tag_ids,
        target_type=target_type,
        signal=signal,
    )


MAX_BULK_TARGET_IDS = 10000
MAX_BULK_NAMES = 100


class BulkEnrichRequest(BaseModel):
    target_ids: list[UUID] = Field(..., min_length=1, max_length=MAX_BULK_TARGET_IDS)
    kind: Literal["whois", "dns", "bgp"]


class BulkTagRequest(BaseModel):
    target_ids: list[UUID] = Field(..., min_length=1, max_length=MAX_BULK_TARGET_IDS)
    tag_names: list[str] = Field(..., min_length=1, max_length=MAX_BULK_NAMES)


class BulkOrgRequest(BaseModel):
    target_ids: list[UUID] = Field(..., min_length=1, max_length=MAX_BULK_TARGET_IDS)
    organization_names: list[str] = Field(..., min_length=1, max_length=MAX_BULK_NAMES)


@router.post("/enrich/bulk", response_model=dict[str, int])
async def bulk_enrich_targets(
    request: BulkEnrichRequest,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    queued = await service.bulk_enrich(request.target_ids, request.kind)
    return {"queued": queued}


@router.post("/tags/bulk", response_model=dict[str, int])
async def bulk_add_tags(
    request: BulkTagRequest,
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    updated = await service.bulk_add_tags(
        request.target_ids, request.tag_names, current_user.id
    )
    return {"updated": updated}


@router.post("/organizations/bulk", response_model=dict[str, int])
async def bulk_add_organizations(
    request: BulkOrgRequest,
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    updated = await service.bulk_add_organizations(
        request.target_ids, request.organization_names, current_user.id
    )
    return {"updated": updated}


@router.get("/search", response_model=Page[TargetRead])
async def search_targets_by_value(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[TargetService, Depends(get_target_service)],
    target_value: Annotated[str, Query(description="Target value to search for")],
    project_slug: Annotated[
        str | None, Query(description="Optional: Filter by specific project")
    ] = None,
):
    query = await service.search_targets_by_value(
        target_value=target_value,
        project_slug=project_slug,
    )

    return await paginate(
        session,
        query,
        transformer=lambda items: [service._to_target_read(t) for t in items],
    )


@router.get("", response_model=Page[TargetRead])
async def list_targets(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[TargetService, Depends(get_target_service)],
    project_slug: Annotated[
        str | None, Query(description="Filter by project slug")
    ] = None,
    search: Annotated[
        str | None, Query(description="Search by target value or display name")
    ] = None,
    organization_ids: Annotated[
        list[UUID] | None, Query(description="Filter by organization IDs")
    ] = None,
    tag_ids: Annotated[
        list[UUID] | None, Query(description="Filter by tag IDs")
    ] = None,
    target_type: Annotated[
        TargetType | None, Query(description="Filter by target type")
    ] = None,
    signal: Annotated[
        SignalName | None,
        Query(description="Filter by signal: expiring, attention, awaiting, enriched"),
    ] = None,
    sort_by: Annotated[SortKey, Query(description="Sort field")] = "updated",
    sort_dir: Annotated[SortDir, Query(description="Sort direction")] = "desc",
):
    query = await service.list_targets(
        project_slug=project_slug,
        search=search,
        organization_ids=organization_ids,
        tag_ids=tag_ids,
        target_type=target_type,
        signal=signal,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    return await paginate(
        session,
        query,
        transformer=lambda items: [service._to_target_read(t) for t in items],
    )


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


@router.post(
    "/import/json",
    response_model=TargetBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_targets_json(
    import_request: TargetImportRequest,
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.import_targets_structured(import_request, current_user.id)


@router.post(
    "/import/csv",
    response_model=TargetBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_targets_csv(
    project_slug: Annotated[
        str, Query(description="Project slug to import targets into")
    ],
    file: Annotated[UploadFile, File(...)],
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.import_targets_csv(project_slug, file, current_user.id)


@router.get("/{target_id}/detail", response_model=TargetDetailRead)
async def get_target_detail(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.get_target_detail(target_id)


@router.get("/{target_id}/dns", response_model=TargetDnsDetailResponse)
async def get_target_dns(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.get_target_dns(target_id)


@router.get("/{target_id}/whois", response_model=TargetWhoisDetailResponse)
async def get_target_whois(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.get_target_whois(target_id)


@router.get("/{target_id}/bgp", response_model=TargetBgpDetailResponse)
async def get_target_bgp(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.get_target_bgp(target_id)


@router.post("/{target_id}/dns/refresh", response_model=EnrichmentRefreshResponse)
async def refresh_target_dns(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.refresh_target_dns(target_id)


@router.post("/{target_id}/whois/refresh", response_model=EnrichmentRefreshResponse)
async def refresh_target_whois(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.refresh_target_whois(target_id)


@router.post("/{target_id}/bgp/refresh", response_model=EnrichmentRefreshResponse)
async def refresh_target_bgp(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    return await service.refresh_target_bgp(target_id)


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
    current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    await service.delete_target(target_id, current_user.id)
