import uuid as _uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.enums.whois import WhoisLookupType
from shared.models.target import Target
from shared.models.whois import (
    WhoisCorrelationResult,
    WhoisRecord,
    WhoisRecordRead,
    WhoisRecordSummary,
)
from tools.whois.service import (
    WhoisError,
    WhoisLookupError,
    WhoisService,
    WhoisValidationError,
)

router = APIRouter(
    prefix="/tools/whois",
    tags=["tools/whois"],
)


def get_whois_service() -> WhoisService:
    return WhoisService()


class WhoisLookupRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Target to look up: domain, IP, CIDR, ASN (e.g. AS13335), or URL",
        examples=["example.com", "8.8.8.8", "192.168.0.0/16", "AS13335"],
    )
    store_in_db: bool = Field(
        default=True,
        description="Cache the result in DB for correlation (default: true)",
    )


class WhoisLookupResponse(BaseModel):
    record: WhoisRecordRead | None = Field(
        default=None,
        description="Stored DB record (null if store_in_db=false)",
    )
    data: dict = Field(
        description="Full parsed WHOIS/RDAP response",
    )
    cached: bool = Field(
        description="Whether this result came from cache",
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
    summary="WHOIS Lookup",
    description="Perform a WHOIS/RDAP lookup. Results are cached in DB by default.",
)
async def whois_lookup(
    request: WhoisLookupRequest,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
):
    try:
        service.ensure_ready()
        cached = False
        if request.store_in_db:
            existing = await session.execute(
                select(WhoisRecord).where(
                    WhoisRecord.query_value == request.query.strip()
                )
            )
            if existing.scalar_one_or_none():
                cached = True

        response = await service.lookup(
            query=request.query,
            store_in_db=request.store_in_db,
            session=session if request.store_in_db else None,
        )

        record_read = None
        if request.store_in_db:
            result = await session.execute(
                select(WhoisRecord).where(WhoisRecord.query_value == response.query)
            )
            db_record = result.scalar_one_or_none()
            if db_record:
                record_read = WhoisRecordRead.model_validate(db_record)

        return WhoisLookupResponse(
            record=record_read,
            data=response.model_dump(mode="json"),
            cached=cached,
        )

    except WhoisValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
    summary="List WHOIS Records",
    description="Browse all cached WHOIS records with optional filters.",
)
async def list_whois_records(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    lookup_type: Annotated[
        WhoisLookupType | None,
        Query(description="Filter by lookup type"),
    ] = None,
    registrant_name: Annotated[
        str | None,
        Query(description="Filter by registrant name (exact match)"),
    ] = None,
    registrar_name: Annotated[
        str | None,
        Query(description="Filter by registrar name (exact match)"),
    ] = None,
    country: Annotated[
        str | None,
        Query(description="Filter by country code (e.g. US, DE)"),
    ] = None,
):
    query = select(WhoisRecord)

    if lookup_type:
        query = query.where(WhoisRecord.lookup_type == lookup_type.value)
    if registrant_name:
        query = query.where(WhoisRecord.registrant_name == registrant_name)
    if registrar_name:
        query = query.where(WhoisRecord.registrar_name == registrar_name)
    if country:
        query = query.where(WhoisRecord.country == country.upper())

    query = query.order_by(WhoisRecord.queried_at.desc())

    return await paginate(session, query)


@router.get(
    "/records/stats",
    response_model=WhoisStatsResponse,
    summary="WHOIS Records Stats",
    description="Aggregate statistics for all cached WHOIS records.",
)
async def whois_records_stats(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    total = await session.scalar(select(func.count(WhoisRecord.id)))

    type_result = await session.execute(
        select(WhoisRecord.lookup_type, func.count(WhoisRecord.id)).group_by(
            WhoisRecord.lookup_type
        )
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    unique_registrants = await session.scalar(
        select(func.count(func.distinct(WhoisRecord.registrant_name))).where(
            WhoisRecord.registrant_name != ""
        )
    )
    unique_registrars = await session.scalar(
        select(func.count(func.distinct(WhoisRecord.registrar_name))).where(
            WhoisRecord.registrar_name != ""
        )
    )
    unique_countries = await session.scalar(
        select(func.count(func.distinct(WhoisRecord.country))).where(
            WhoisRecord.country != ""
        )
    )
    unique_networks = await session.scalar(
        select(func.count(func.distinct(WhoisRecord.network_cidr))).where(
            WhoisRecord.network_cidr != ""
        )
    )

    return WhoisStatsResponse(
        total_records=total or 0,
        by_lookup_type=by_type,
        unique_registrants=unique_registrants or 0,
        unique_registrars=unique_registrars or 0,
        unique_countries=unique_countries or 0,
        unique_networks=unique_networks or 0,
    )


@router.get(
    "/records/{record_id}",
    response_model=WhoisRecordRead,
    summary="Get WHOIS Record",
    description="Get a single cached WHOIS record by ID with full parsed data.",
)
async def get_whois_record(
    record_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(WhoisRecord).where(WhoisRecord.id == record_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WHOIS record not found",
        )

    return WhoisRecordRead.model_validate(record)


@router.post(
    "/records/{record_id}/refresh",
    response_model=WhoisRefreshResponse,
    summary="Refresh WHOIS Record",
    description="Force re-query RDAP for an existing record, ignoring cache TTL.",
)
async def refresh_whois_record(
    record_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
):
    result = await session.execute(
        select(WhoisRecord).where(WhoisRecord.id == record_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WHOIS record not found",
        )

    previous_queried_at = record.queried_at.isoformat() if record.queried_at else None

    try:
        service.ensure_ready()

        original_ttl = service.cache_ttl_days
        service.cache_ttl_days = 0
        await service.lookup(
            query=record.query_value,
            store_in_db=True,
            session=session,
        )
        service.cache_ttl_days = original_ttl

        await session.refresh(record)

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
    summary="Get WHOIS Record by Target",
    description="Get the cached WHOIS record linked to a specific target.",
)
async def get_whois_record_by_target(
    target_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    target_result = await session.execute(select(Target).where(Target.id == target_id))
    target = target_result.scalar_one_or_none()

    if not target or not target.whois_record_id:
        return None

    result = await session.execute(
        select(WhoisRecord).where(WhoisRecord.id == target.whois_record_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        return None

    return WhoisRecordRead.model_validate(record)


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete WHOIS Record",
    description="Delete a cached WHOIS record.",
)
async def delete_whois_record(
    record_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(WhoisRecord).where(WhoisRecord.id == record_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WHOIS record not found",
        )

    await session.delete(record)
    await session.commit()


@router.get(
    "/correlations/target/{target_id}",
    response_model=list[WhoisCorrelationResult],
    summary="Get Target Correlations",
    description=(
        "Find all targets related to the given target through shared WHOIS data. "
        "Returns groups by correlation type: registrant, registrar, nameserver, "
        "network block, and country."
    ),
)
async def get_target_correlations(
    target_id: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
):
    try:
        tid = _uuid.UUID(target_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target_id format",
        ) from e

    # get target to find its whois_record_id
    target_result = await session.execute(select(Target).where(Target.id == tid))
    target = target_result.scalar_one_or_none()

    if not target or not target.whois_record_id:
        return []

    correlations = await service.get_correlations_for_target(
        session, target.whois_record_id
    )

    if not correlations:
        return []

    # get the target's own whois record for correlation values
    target_record_result = await session.execute(
        select(WhoisRecord).where(WhoisRecord.id == target.whois_record_id)
    )
    target_record = target_record_result.scalar_one_or_none()

    results = []
    value_field_map = {
        "registrant_name": "registrant_name",
        "registrar_name": "registrar_name",
        "network_cidr": "network_cidr",
        "country": "country",
        "nameserver": None,
    }

    for corr_type, records in correlations.items():
        if corr_type == "nameserver" and target_record and target_record.nameservers:
            corr_value = ", ".join(target_record.nameservers)
        elif target_record and corr_type in value_field_map:
            field = value_field_map.get(corr_type, corr_type)
            corr_value = getattr(target_record, field, "") if field else ""
        else:
            corr_value = corr_type

        summaries = [_to_summary(r) for r in records]

        results.append(
            WhoisCorrelationResult(
                correlation_type=corr_type,
                correlation_value=corr_value,
                records=summaries,
                count=len(summaries),
            )
        )

    return results


@router.get(
    "/correlations/registrant",
    response_model=list[WhoisCorrelationResult],
    summary="Find by Registrant",
    description="Find all WHOIS records sharing the same registrant name.",
)
async def correlate_by_registrant(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    name: Annotated[str, Query(description="Registrant name to search for")],
):
    results = await session.execute(
        select(WhoisRecord)
        .where(WhoisRecord.registrant_name == name)
        .where(WhoisRecord.registrant_name != "")
    )
    records = list(results.scalars().all())

    if not records:
        return []

    return [
        WhoisCorrelationResult(
            correlation_type="registrant_name",
            correlation_value=name,
            records=[_to_summary(r) for r in records],
            count=len(records),
        )
    ]


@router.get(
    "/correlations/registrar",
    response_model=list[WhoisCorrelationResult],
    summary="Find by Registrar",
    description="Find all WHOIS records sharing the same registrar.",
)
async def correlate_by_registrar(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    name: Annotated[str, Query(description="Registrar name to search for")],
):
    results = await session.execute(
        select(WhoisRecord)
        .where(WhoisRecord.registrar_name == name)
        .where(WhoisRecord.registrar_name != "")
    )
    records = list(results.scalars().all())

    if not records:
        return []

    return [
        WhoisCorrelationResult(
            correlation_type="registrar_name",
            correlation_value=name,
            records=[_to_summary(r) for r in records],
            count=len(records),
        )
    ]


@router.get(
    "/correlations/network",
    response_model=list[WhoisCorrelationResult],
    summary="Find by Network",
    description="Find all WHOIS records in the same network CIDR block.",
)
async def correlate_by_network(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    cidr: Annotated[
        str, Query(description="Network CIDR to search for (e.g. 8.8.8.0/24)")
    ],
):
    results = await session.execute(
        select(WhoisRecord)
        .where(WhoisRecord.network_cidr == cidr)
        .where(WhoisRecord.network_cidr != "")
    )
    records = list(results.scalars().all())

    if not records:
        return []

    return [
        WhoisCorrelationResult(
            correlation_type="network_cidr",
            correlation_value=cidr,
            records=[_to_summary(r) for r in records],
            count=len(records),
        )
    ]


@router.get(
    "/correlations/country",
    response_model=list[WhoisCorrelationResult],
    summary="Find by Country",
    description="Find all WHOIS records registered in a specific country.",
)
async def correlate_by_country(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    code: Annotated[str, Query(description="Country code (e.g. US, DE, JP)")],
):
    results = await session.execute(
        select(WhoisRecord)
        .where(WhoisRecord.country == code.upper())
        .where(WhoisRecord.country != "")
    )
    records = list(results.scalars().all())

    if not records:
        return []

    return [
        WhoisCorrelationResult(
            correlation_type="country",
            correlation_value=code.upper(),
            records=[_to_summary(r) for r in records],
            count=len(records),
        )
    ]


@router.get(
    "/correlations/nameserver",
    response_model=list[WhoisCorrelationResult],
    summary="Find by Nameserver",
    description="Find all domain records sharing a specific nameserver.",
)
async def correlate_by_nameserver(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    ns: Annotated[str, Query(description="Nameserver hostname (e.g. ns1.google.com)")],
):
    results = await session.execute(
        select(WhoisRecord).where(WhoisRecord.nameservers.op("@>")(f'["{ns}"]'))
    )
    records = list(results.scalars().all())

    if not records:
        return []

    return [
        WhoisCorrelationResult(
            correlation_type="nameserver",
            correlation_value=ns,
            records=[_to_summary(r) for r in records],
            count=len(records),
        )
    ]


def _to_summary(record: WhoisRecord) -> WhoisRecordSummary:
    return WhoisRecordSummary(
        id=record.id,
        query_value=record.query_value,
        lookup_type=record.lookup_type,
        name=record.name,
        registrant_name=record.registrant_name,
        registrar_name=record.registrar_name,
        country=record.country,
        network_cidr=record.network_cidr,
        registration_date=record.registration_date,
        expiration_date=record.expiration_date,
        queried_at=record.queried_at,
    )
