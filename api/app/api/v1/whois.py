import uuid as _uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import apaginate
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from app.services.whois_record import WhoisRecordService, correlation_results
from shared.enums.whois import WhoisLookupType
from shared.models.whois import (
    WhoisCorrelationResult,
    WhoisRecordRead,
    WhoisRecordSummary,
)
from tools.whois.service import (
    WhoisError,
    WhoisLookupError,
    WhoisNotApplicableError,
    WhoisService,
    WhoisValidationError,
)

router = APIRouter(
    prefix="/tools/whois",
    tags=["tools/whois"],
)


def get_whois_service() -> WhoisService:
    return WhoisService()


def get_record_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    whois: Annotated[WhoisService, Depends(get_whois_service)],
) -> WhoisRecordService:
    return WhoisRecordService(session, whois)


class WhoisLookupRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Domain, IP, CIDR, ASN or URL",
        examples=["example.com", "8.8.8.8", "192.168.0.0/16", "AS13335"],
    )
    store_in_db: bool = Field(
        default=True,
        description="Store the result for correlation",
    )


class WhoisLookupResponse(BaseModel):
    record: WhoisRecordRead | None = Field(
        default=None,
        description="Stored record. Null when store_in_db is false.",
    )
    data: dict = Field(
        description="Full parsed WHOIS/RDAP response",
    )
    cached: bool = Field(
        description="Served from cache",
    )


class WhoisRefreshResponse(BaseModel):
    record: WhoisRecordRead
    previous_queried_at: str | None


class WhoisStatsResponse(BaseModel):
    total_records: int
    by_lookup_type: dict[str, int]
    unique_registrants: int
    unique_registrars: int
    unique_countries: int
    unique_networks: int


@router.post(
    "/lookup",
    response_model=WhoisLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="WHOIS lookup",
    description="WHOIS/RDAP lookup. Results are cached.",
)
async def whois_lookup(
    request: WhoisLookupRequest,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    try:
        service.ensure_ready()

        result = await service.lookup(
            query=request.query,
            store_in_db=request.store_in_db,
            session=session if request.store_in_db else None,
        )
        response = result.response

        record_read = None
        if request.store_in_db:
            db_record = await records.stored(response.query)
            if db_record:
                record_read = WhoisRecordRead.model_validate(db_record)

        return WhoisLookupResponse(
            record=record_read,
            data=response.model_dump(mode="json"),
            cached=result.cache_hit,
        )

    except WhoisValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except WhoisNotApplicableError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except WhoisLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WHOIS lookup failed: {e}",
        ) from e
    except WhoisError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WHOIS service error: {e}",
        ) from e


@router.get(
    "/records",
    response_model=Page[WhoisRecordSummary],
    summary="List WHOIS records",
    description="Cached WHOIS records.",
)
async def list_whois_records(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
    lookup_type: Annotated[
        WhoisLookupType | None,
        Query(description="Filter by lookup type"),
    ] = None,
    registrant_name: Annotated[
        str | None,
        Query(description="Exact registrant name"),
    ] = None,
    registrar_name: Annotated[
        str | None,
        Query(description="Exact registrar name"),
    ] = None,
    country: Annotated[
        str | None,
        Query(description="Two-letter country code"),
    ] = None,
):
    query = records.list_query(
        lookup_type=lookup_type,
        registrant_name=registrant_name,
        registrar_name=registrar_name,
        country=country,
    )
    return await apaginate(session, query)


@router.get(
    "/records/stats",
    response_model=WhoisStatsResponse,
    summary="WHOIS record stats",
    description="Counts across cached WHOIS records.",
)
async def whois_records_stats(
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    return WhoisStatsResponse(**await records.stats())


@router.get(
    "/records/{record_id}",
    response_model=WhoisRecordRead,
    summary="Get WHOIS record",
    description="One cached WHOIS record with parsed data.",
)
async def get_whois_record(
    record_id: str,
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    return WhoisRecordRead.model_validate(await records.get(record_id))


@router.post(
    "/records/{record_id}/refresh",
    response_model=WhoisRefreshResponse,
    summary="Refresh WHOIS record",
    description="Re-query RDAP for the record.",
)
async def refresh_whois_record(
    record_id: str,
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    try:
        record, previous_queried_at = await records.refresh(record_id)
        return WhoisRefreshResponse(
            record=WhoisRecordRead.model_validate(record),
            previous_queried_at=previous_queried_at,
        )
    except WhoisError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WHOIS refresh failed: {e}",
        ) from e


@router.get(
    "/records/by-target/{target_id}",
    response_model=WhoisRecordRead | None,
    summary="WHOIS record by target",
    description="The cached WHOIS record linked to a target.",
)
async def get_whois_record_by_target(
    target_id: str,
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    record = await records.for_target(target_id)
    return WhoisRecordRead.model_validate(record) if record else None


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete WHOIS record",
    description="Remove a cached WHOIS record.",
)
async def delete_whois_record(
    record_id: str,
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    await records.delete(record_id)


@router.get(
    "/correlations/targets",
    response_model=dict[str, list[WhoisCorrelationResult]],
    summary="Correlations for several targets",
)
async def get_targets_correlations(
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
    ids: Annotated[str, Query(description="Comma-separated target IDs")],
):
    wanted = []
    for raw in ids.split(","):
        try:
            wanted.append(_uuid.UUID(raw.strip()))
        except ValueError:
            continue
    if not wanted:
        return {}
    return await records.correlations_for_targets(wanted)


@router.get(
    "/correlations/target/{target_id}",
    response_model=list[WhoisCorrelationResult],
    summary="Target correlations",
    description="Targets sharing WHOIS data, grouped by registrant, registrar, nameserver, network block and country.",
)
async def get_target_correlations(
    target_id: str,
    _current_user: CurrentUser,
    records: Annotated[WhoisRecordService, Depends(get_record_service)],
):
    try:
        tid = _uuid.UUID(target_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target ID",
        ) from e
    return await records.correlations_for_target(tid)


@router.get(
    "/correlations/registrant",
    response_model=list[WhoisCorrelationResult],
    summary="Find by registrant",
    description="WHOIS records with the same registrant name.",
)
async def correlate_by_registrant(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
    name: Annotated[str, Query(description="Registrant name")],
):
    records = await service.find_by_registrant(session, name)
    return correlation_results("registrant_name", name, records)


@router.get(
    "/correlations/registrar",
    response_model=list[WhoisCorrelationResult],
    summary="Find by registrar",
    description="WHOIS records with the same registrar.",
)
async def correlate_by_registrar(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
    name: Annotated[str, Query(description="Registrar name")],
):
    records = await service.find_by_registrar(session, name)
    return correlation_results("registrar_name", name, records)


@router.get(
    "/correlations/network",
    response_model=list[WhoisCorrelationResult],
    summary="Find by network",
    description="WHOIS records in one network block.",
)
async def correlate_by_network(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
    cidr: Annotated[str, Query(description="Network CIDR such as 8.8.8.0/24")],
):
    records = await service.find_by_network(session, cidr)
    return correlation_results("network_cidr", cidr, records)


@router.get(
    "/correlations/country",
    response_model=list[WhoisCorrelationResult],
    summary="Find by country",
    description="WHOIS records registered in one country.",
)
async def correlate_by_country(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
    code: Annotated[str, Query(description="Two-letter country code")],
):
    records = await service.find_by_country(session, code)
    return correlation_results("country", code.upper(), records)


@router.get(
    "/correlations/nameserver",
    response_model=list[WhoisCorrelationResult],
    summary="Find by nameserver",
    description="Domain records with the same nameserver.",
)
async def correlate_by_nameserver(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
    ns: Annotated[
        str, Query(description="Nameserver host name such as ns1.google.com")
    ],
):
    records = await service.find_by_nameserver(session, ns)
    return correlation_results("nameserver", ns, records)
