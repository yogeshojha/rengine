"""Stored WHOIS records: listed, counted, refreshed and correlated across targets."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select

from shared.models.target import Target
from shared.models.whois import (
    WhoisCorrelationResult,
    WhoisRecord,
    WhoisRecordSummary,
)
from tools.whois.service import WhoisService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.enums.whois import WhoisLookupType

_RECORD_NOT_FOUND = "WHOIS record not found"
MAX_CORRELATED_TARGETS = 100

# the record column a correlation type names; a nameserver correlation lists them all
_CORRELATION_FIELDS = {
    "registrant_name": "registrant_name",
    "registrar_name": "registrar_name",
    "network_cidr": "network_cidr",
    "country": "country",
    "nameserver": None,
}


def to_summary(
    record: WhoisRecord, target_id: uuid.UUID | None = None
) -> WhoisRecordSummary:
    return WhoisRecordSummary(
        id=record.id,
        target_id=target_id,
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


def correlation_results(
    correlation_type: str,
    correlation_value: str,
    records: list[WhoisRecord],
) -> list[WhoisCorrelationResult]:
    """One correlation group of these records, or none when there are no records."""
    if not records:
        return []
    return [
        WhoisCorrelationResult(
            correlation_type=correlation_type,
            correlation_value=correlation_value,
            records=[to_summary(r) for r in records],
            count=len(records),
        )
    ]


def _correlation_value(corr_type: str, target_record: WhoisRecord | None) -> str:
    """What the target's own record holds for this correlation type."""
    if corr_type == "nameserver" and target_record and target_record.nameservers:
        return ", ".join(target_record.nameservers)
    if target_record and corr_type in _CORRELATION_FIELDS:
        field = _CORRELATION_FIELDS[corr_type]
        return getattr(target_record, field, "") if field else ""
    return corr_type


class WhoisRecordService:
    def __init__(self, session: AsyncSession, whois: WhoisService | None = None):
        self.session = session
        self.whois = whois or WhoisService()

    async def stored(self, query_value: str) -> WhoisRecord | None:
        """The record a lookup of this value stored, if any."""
        return await self.session.scalar(
            select(WhoisRecord).where(WhoisRecord.query_value == query_value)
        )

    def list_query(
        self,
        *,
        lookup_type: WhoisLookupType | None = None,
        registrant_name: str | None = None,
        registrar_name: str | None = None,
        country: str | None = None,
    ) -> Select:
        query = select(WhoisRecord)
        if lookup_type:
            query = query.where(WhoisRecord.lookup_type == lookup_type.value)
        if registrant_name:
            query = query.where(WhoisRecord.registrant_name == registrant_name)
        if registrar_name:
            query = query.where(WhoisRecord.registrar_name == registrar_name)
        if country:
            query = query.where(WhoisRecord.country == country.upper())
        return query.order_by(WhoisRecord.queried_at.desc())

    async def stats(self) -> dict:
        """Counts across every stored record."""
        by_type = await self.session.execute(
            select(WhoisRecord.lookup_type, func.count(WhoisRecord.id)).group_by(
                WhoisRecord.lookup_type
            )
        )
        return {
            "total_records": await self.session.scalar(
                select(func.count(WhoisRecord.id))
            )
            or 0,
            "by_lookup_type": {row[0]: row[1] for row in by_type.all()},
            "unique_registrants": await self._distinct(WhoisRecord.registrant_name),
            "unique_registrars": await self._distinct(WhoisRecord.registrar_name),
            "unique_countries": await self._distinct(WhoisRecord.country),
            "unique_networks": await self._distinct(WhoisRecord.network_cidr),
        }

    async def get(self, record_id: str) -> WhoisRecord:
        record = await self.session.scalar(
            select(WhoisRecord).where(WhoisRecord.id == record_id)
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_RECORD_NOT_FOUND
            )
        return record

    async def refresh(self, record_id: str) -> tuple[WhoisRecord, str | None]:
        """Re-query the record past the cache; the record and when it was last queried."""
        record = await self.get(record_id)
        previous = record.queried_at.isoformat() if record.queried_at else None
        fresh = WhoisService(cache_ttl_days=0)
        fresh.ensure_ready()
        await fresh.lookup(
            query=record.query_value, store_in_db=True, session=self.session
        )
        await self.session.refresh(record)
        return record, previous

    async def for_target(self, target_id: str) -> WhoisRecord | None:
        target = await self.session.scalar(select(Target).where(Target.id == target_id))
        if target is None or not target.whois_record_id:
            return None
        return await self.session.scalar(
            select(WhoisRecord).where(WhoisRecord.id == target.whois_record_id)
        )

    async def delete(self, record_id: str) -> None:
        record = await self.get(record_id)
        await self.session.delete(record)
        await self.session.commit()

    async def correlations_for_target(
        self, target_id: uuid.UUID
    ) -> list[WhoisCorrelationResult]:
        target = await self.session.scalar(select(Target).where(Target.id == target_id))
        if target is None:
            return []
        return await self._correlations(target)

    async def correlations_for_targets(
        self, target_ids: list[uuid.UUID]
    ) -> dict[str, list[WhoisCorrelationResult]]:
        rows = await self.session.scalars(
            select(Target).where(Target.id.in_(target_ids[:MAX_CORRELATED_TARGETS]))
        )
        return {
            str(target.id): await self._correlations(target) for target in rows.all()
        }

    async def _correlations(self, target: Target) -> list[WhoisCorrelationResult]:
        """Records sharing WHOIS data with this target's, each linked to its target."""
        if not target.whois_record_id:
            return []
        correlations = await self.whois.get_correlations_for_target(
            self.session, target.whois_record_id
        )
        if not correlations:
            return []

        target_record = await self.session.scalar(
            select(WhoisRecord).where(WhoisRecord.id == target.whois_record_id)
        )
        record_ids = {r.id for records in correlations.values() for r in records}
        linked = await self.session.execute(
            select(Target.whois_record_id, Target.id).where(
                Target.project_id == target.project_id,
                Target.whois_record_id.in_(record_ids),
            )
        )
        target_by_record = dict(linked.all())

        results = []
        for corr_type, records in correlations.items():
            summaries = [
                to_summary(r, target_id=target_by_record.get(r.id)) for r in records
            ]
            results.append(
                WhoisCorrelationResult(
                    correlation_type=corr_type,
                    correlation_value=_correlation_value(corr_type, target_record),
                    records=summaries,
                    count=len(summaries),
                )
            )
        return results

    async def _distinct(self, column) -> int:
        return (
            await self.session.scalar(
                select(func.count(func.distinct(column))).where(column != "")
            )
            or 0
        )
