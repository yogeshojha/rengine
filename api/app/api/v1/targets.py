from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
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
    """
    Validate multiple target values in one request.
    Maximum as defined in {MAX_TARGET_IMPORT} targets per request.
    """
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
    """Per-signal KPI counts over the same filtered base set as the list."""
    return await service.get_target_stats(
        project_slug=project_slug,
        search=search,
        organization_ids=organization_ids,
        tag_ids=tag_ids,
        target_type=target_type,
    )


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
    """
    Search for targets by their target_value across all projects.
    Returns all instances of a target (which may exist in multiple projects).
    Optionally uses filter by project_slug to narrow results.
    """
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
    """
    Import targets from JSON with per-target customization.

    Each target can have its own tags and organizations.
    Maximum 500 targets per request, later todo in celery.

    Example SUpported:
    {
      "project_slug": "my-project",
      "targets": [
        {
          "target_value": "loremipsum.com",
          "tags": ["production", "critical"],
          "organizations": ["Hello World"],
          "display_name": "Main Website"
        },
        {
          "target_value": "192.168.1.1",
          "tags": ["internal"],
          "organizations": []
        }
      ]
    }
    """
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
    """
    Import targets from a CSV file.

    CSV Format Options:
    1. Simple (single column): target_value
    2. With tags: target_value, tags (comma-separated)
    3. With organizations: target_value, organizations (comma-separated)
    4. Full: target_value, tags, organizations, display_name

    Headers are optional but recommended. If no headers, assumes first column is target_value.
    Flexible header names: target/value/domain/ip, tags/tag, organizations/org, display_name/name

    Each target can have its own tags and organizations (comma-separated in CSV cells).
    Maximum 500 targets per CSV file.
    """
    return await service.import_targets_csv(project_slug, file, current_user.id)


@router.get("/{target_id}/detail", response_model=TargetDetailRead)
async def get_target_detail(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Get complete target with all enrichment data expanded.

    Returns the target with full WHOIS record, full DNS lookup
    with all records, and full BGP data from RIPEStat tables.
    """
    return await service.get_target_detail(target_id)


@router.get("/{target_id}/dns", response_model=TargetDnsDetailResponse)
async def get_target_dns(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Get full DNS lookup data with all individual records."""
    return await service.get_target_dns(target_id)


@router.get("/{target_id}/whois", response_model=TargetWhoisDetailResponse)
async def get_target_whois(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Get full WHOIS record for a target."""
    return await service.get_target_whois(target_id)


@router.get("/{target_id}/bgp", response_model=TargetBgpDetailResponse)
async def get_target_bgp(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Get full BGP enrichment data from RIPEStat tables.

    Response varies by target type:
    - ASN: AS overview, announced prefixes, neighbours, abuse contacts
    - IP: network info, AS overview, abuse contacts
    - IP_RANGE: prefix overview, related prefixes, abuse contacts
    - DOMAIN/URL: returns status only, no BGP data
    """
    return await service.get_target_bgp(target_id)


@router.post("/{target_id}/dns/refresh", response_model=EnrichmentRefreshResponse)
async def refresh_target_dns(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Re-trigger DNS lookup. Only for DOMAIN and URL targets (422 otherwise)."""
    return await service.refresh_target_dns(target_id)


@router.post("/{target_id}/whois/refresh", response_model=EnrichmentRefreshResponse)
async def refresh_target_whois(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Re-trigger WHOIS lookup. Applies to all target types."""
    return await service.refresh_target_whois(target_id)


@router.post("/{target_id}/bgp/refresh", response_model=EnrichmentRefreshResponse)
async def refresh_target_bgp(
    target_id: str,
    _current_user: CurrentUser,
    service: Annotated[TargetService, Depends(get_target_service)],
):
    """Re-trigger BGP enrichment. Only for IP, IP_RANGE, and ASN targets (422 otherwise)."""
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
