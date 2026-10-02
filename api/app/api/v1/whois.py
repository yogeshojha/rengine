import uuid as _uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.enums.target import TargetType
from shared.enums.whois import WhoisLookupType
from shared.http import egress_proxy
from shared.models.target import Target
from shared.models.whois import (
    WhoisCorrelationResult,
    WhoisRecord,
    WhoisRecordRead,
    WhoisRecordSummary,
)
from shared.utils.infra import is_shared_nameserver
from tools.whois.service import WhoisError, WhoisService

router = APIRouter(
    prefix="/tools/whois",
    tags=["tools/whois"],
)


def get_whois_service() -> WhoisService:
    return WhoisService(proxy_url=egress_proxy())


class WhoisRefreshResponse(BaseModel):
    record: WhoisRecordRead
    previous_queried_at: str | None


@router.get(
    "/records/{record_id}",
    response_model=WhoisRecordRead,
    summary="Get WHOIS record",
    description="One cached WHOIS record with parsed data.",
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
    summary="Refresh WHOIS record",
    description="Re-query RDAP for the record.",
)
async def refresh_whois_record(
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

    previous_queried_at = record.queried_at.isoformat() if record.queried_at else None

    service = WhoisService(cache_ttl_days=0, proxy_url=egress_proxy())
    try:
        await service.lookup(
            query=record.query_value,
            target_type=TargetType.ASN
            if record.lookup_type == WhoisLookupType.ASN
            else None,
            store_in_db=True,
            session=session,
        )

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


async def _target_correlations(
    session: AsyncSession, service: WhoisService, target: Target
) -> list[WhoisCorrelationResult]:
    if not target.whois_record_id:
        return []

    correlations = await service.get_correlations_for_target(
        session, target.whois_record_id
    )

    if not correlations:
        return []

    target_record_result = await session.execute(
        select(WhoisRecord).where(WhoisRecord.id == target.whois_record_id)
    )
    target_record = target_record_result.scalar_one_or_none()

    record_ids = {r.id for records in correlations.values() for r in records}
    linked = await session.execute(
        select(Target.whois_record_id, Target.id).where(
            Target.project_id == target.project_id,
            Target.whois_record_id.in_(record_ids),
        )
    )
    target_by_record = dict(linked.all())

    results = []
    value_field_map = {
        "registrant_name": "registrant_name",
        "network_cidr": "network_cidr",
        "nameserver": None,
    }

    for corr_type, records in correlations.items():
        summaries = [
            _to_summary(r, target_id=target_by_record[r.id])
            for r in records
            if r.id in target_by_record
        ]
        if not summaries:
            continue

        if corr_type == "nameserver" and target_record and target_record.nameservers:
            corr_value = ", ".join(
                ns
                for ns in target_record.nameservers
                if ns and not is_shared_nameserver(ns)
            )
        elif target_record and corr_type in value_field_map:
            field = value_field_map.get(corr_type, corr_type)
            corr_value = getattr(target_record, field, "") if field else ""
        else:
            corr_value = corr_type

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
    "/correlations/targets",
    response_model=dict[str, list[WhoisCorrelationResult]],
    summary="Correlations for several targets",
)
async def get_targets_correlations(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[WhoisService, Depends(get_whois_service)],
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
    rows = await session.execute(select(Target).where(Target.id.in_(wanted[:100])))
    out: dict[str, list[WhoisCorrelationResult]] = {}
    for target in rows.scalars().all():
        out[str(target.id)] = await _target_correlations(session, service, target)
    return out


@router.get(
    "/correlations/target/{target_id}",
    response_model=list[WhoisCorrelationResult],
    summary="Target correlations",
    description="Targets sharing WHOIS data, grouped by registrant, nameserver and network block.",
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
            detail="Invalid target ID",
        ) from e

    target_result = await session.execute(select(Target).where(Target.id == tid))
    target = target_result.scalar_one_or_none()
    if not target:
        return []
    return await _target_correlations(session, service, target)


async def _correlation_results(
    session: AsyncSession,
    project_id: _uuid.UUID,
    correlation_type: str,
    correlation_value: str,
    records: list[WhoisRecord],
) -> list[WhoisCorrelationResult]:
    if not records:
        return []
    linked = await session.execute(
        select(Target.whois_record_id, Target.id).where(
            Target.project_id == project_id,
            Target.whois_record_id.in_([r.id for r in records]),
        )
    )
    target_by_record = dict(linked.all())
    return [
        WhoisCorrelationResult(
            correlation_type=correlation_type,
            correlation_value=correlation_value,
            records=[
                _to_summary(r, target_id=target_by_record.get(r.id)) for r in records
            ],
            count=len(records),
        )
    ]


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
    project_id: Annotated[_uuid.UUID, Query(description="Project ID")],
):
    records = await service.find_by_registrant(session, name)
    return await _correlation_results(
        session, project_id, "registrant_name", name, records
    )


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
    project_id: Annotated[_uuid.UUID, Query(description="Project ID")],
):
    records = await service.find_by_registrar(session, name)
    return await _correlation_results(
        session, project_id, "registrar_name", name, records
    )


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
    project_id: Annotated[_uuid.UUID, Query(description="Project ID")],
):
    records = await service.find_by_network(session, cidr)
    return await _correlation_results(
        session, project_id, "network_cidr", cidr, records
    )


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
    project_id: Annotated[_uuid.UUID, Query(description="Project ID")],
):
    records = await service.find_by_nameserver(session, ns)
    return await _correlation_results(session, project_id, "nameserver", ns, records)


def _to_summary(
    record: WhoisRecord, target_id: _uuid.UUID | None = None
) -> WhoisRecordSummary:
    return WhoisRecordSummary(
        id=record.id,
        target_id=target_id,
        query_value=record.query_value,
        lookup_type=record.lookup_type,
        name=record.name,
        registrant_name=record.registrant_name,
        registrant_email=record.registrant_email,
        registrar_name=record.registrar_name,
        nameservers=record.nameservers,
        country=record.country,
        network_cidr=record.network_cidr,
        registration_date=record.registration_date,
        expiration_date=record.expiration_date,
        queried_at=record.queried_at,
    )
