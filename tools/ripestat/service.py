"""RIPEstat service — structured BGP data with caching."""

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlmodel import select

from shared.enums.ripestat import RIPEStatLookupType
from shared.logging import get_logger
from shared.models.ripestat import (
    RIPEStatAbuseContact,
    RIPEStatAnnouncedPrefix,
    RIPEStatASNNeighbour,
    RIPEStatASOverview,
    RIPEStatNetworkInfo,
    RIPEStatPrefixOverview,
    RIPEStatQueryLog,
    RIPEStatRelatedPrefix,
)
from shared.utils.datetime import utc_now
from tools.ripestat.client import RIPEStatAPIError, RIPEStatClient
from tools.ripestat.models import (
    AbuseContactRead,
    AnnouncedPrefixRead,
    ASNNeighbourRead,
    ASOverviewRead,
    NetworkInfoRead,
    PrefixOverviewRead,
    RelatedPrefixRead,
    RIPEStatResult,
)
from tools.ripestat.parser import (
    parse_abuse_contact,
    parse_announced_prefixes,
    parse_as_overview,
    parse_asn_neighbours,
    parse_network_info,
    parse_prefix_overview,
    parse_related_prefixes,
)

logger = get_logger(__name__)

DEFAULT_CACHE_TTL_DAYS = 7


class RIPEStatError(Exception):
    """Base exception for RIPEstat service."""


class RIPEStatLookupError(RIPEStatError):
    """Lookup failed."""


def _normalize_asn(raw: str) -> int:
    """'AS23752', 'as23752', '23752' -> 23752"""
    return int(raw.upper().replace("AS", "").strip())


def _asn_resource(asn: int) -> str:
    """Int ASN -> API resource string."""
    return f"AS{asn}"


class RIPEStatService:
    def __init__(
        self,
        session: AsyncSession | None = None,
        cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS,
    ) -> None:
        self._session = session
        self._client = RIPEStatClient()
        self.cache_ttl_days = cache_ttl_days

    def _is_fresh(self, log: RIPEStatQueryLog) -> bool:
        if not log.queried_at:
            return False
        return (utc_now() - log.queried_at) < timedelta(days=self.cache_ttl_days)

    def _to_result(
        self,
        lookup_type: RIPEStatLookupType,
        query_value: str,
        data,
        result_count: int,
        cached: bool = False,
        queried_at=None,
    ) -> RIPEStatResult:
        return RIPEStatResult(
            lookup_type=lookup_type,
            query_value=query_value,
            result_count=result_count,
            cached=cached,
            queried_at=queried_at or utc_now(),
            data=data,
        )

    async def _get_query_log(
        self, lookup_type: RIPEStatLookupType, query_value: str
    ) -> RIPEStatQueryLog | None:
        result = await self._session.execute(
            select(RIPEStatQueryLog).where(
                RIPEStatQueryLog.lookup_type == lookup_type.value,
                RIPEStatQueryLog.query_value == query_value,
            )
        )
        return result.scalar_one_or_none()

    async def _update_query_log(
        self, lookup_type: RIPEStatLookupType, query_value: str, result_count: int
    ) -> None:
        now = utc_now()
        existing = await self._get_query_log(lookup_type, query_value)
        if existing:
            existing.result_count = result_count
            existing.queried_at = now
            existing.updated_at = now
            self._session.add(existing)
        else:
            self._session.add(
                RIPEStatQueryLog(
                    lookup_type=lookup_type.value,
                    query_value=query_value,
                    result_count=result_count,
                    queried_at=now,
                )
            )

    def _get_query_log_sync(
        self, session: Session, lookup_type: RIPEStatLookupType, query_value: str
    ) -> RIPEStatQueryLog | None:
        result = session.execute(
            select(RIPEStatQueryLog).where(
                RIPEStatQueryLog.lookup_type == lookup_type.value,
                RIPEStatQueryLog.query_value == query_value,
            )
        )
        return result.scalar_one_or_none()

    def _update_query_log_sync(
        self,
        session: Session,
        lookup_type: RIPEStatLookupType,
        query_value: str,
        result_count: int,
    ) -> None:
        now = utc_now()
        existing = self._get_query_log_sync(session, lookup_type, query_value)
        if existing:
            existing.result_count = result_count
            existing.queried_at = now
            existing.updated_at = now
            session.add(existing)
        else:
            session.add(
                RIPEStatQueryLog(
                    lookup_type=lookup_type.value,
                    query_value=query_value,
                    result_count=result_count,
                    queried_at=now,
                )
            )

    # fastapi async methods (API handlers)

    async def announced_prefixes(
        self, raw_asn: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        asn = _normalize_asn(raw_asn)
        query_value = str(asn)
        lookup_type = RIPEStatLookupType.ANNOUNCED_PREFIXES

        log = await self._get_query_log(lookup_type, query_value)
        if log and self._is_fresh(log):
            rows = (
                (
                    await self._session.execute(
                        select(RIPEStatAnnouncedPrefix).where(
                            RIPEStatAnnouncedPrefix.asn == asn
                        )
                    )
                )
                .scalars()
                .all()
            )
            data = [
                AnnouncedPrefixRead(
                    prefix=r.prefix,
                    ip_version=r.ip_version,
                    first_seen=r.first_seen,
                    last_seen=r.last_seen,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                query_value,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = await self._client.announced_prefixes(_asn_resource(asn))
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_announced_prefixes(raw, asn)

        # delete stale + insert fresh
        await self._session.execute(
            delete(RIPEStatAnnouncedPrefix).where(RIPEStatAnnouncedPrefix.asn == asn)
        )
        now = utc_now()
        for p in parsed.prefixes:
            self._session.add(
                RIPEStatAnnouncedPrefix(
                    asn=asn,
                    prefix=p.prefix,
                    ip_version=p.ip_version,
                    first_seen=p.first_seen,
                    last_seen=p.last_seen,
                    queried_at=now,
                )
            )
        await self._update_query_log(lookup_type, query_value, len(parsed.prefixes))
        await self._session.commit()

        data = [
            AnnouncedPrefixRead(
                prefix=p.prefix,
                ip_version=p.ip_version,
                first_seen=p.first_seen,
                last_seen=p.last_seen,
            )
            for p in parsed.prefixes
        ]
        return self._to_result(lookup_type, query_value, data, len(parsed.prefixes))

    async def asn_neighbours(
        self, raw_asn: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        asn = _normalize_asn(raw_asn)
        query_value = str(asn)
        lookup_type = RIPEStatLookupType.ASN_NEIGHBOURS

        log = await self._get_query_log(lookup_type, query_value)
        if log and self._is_fresh(log):
            rows = (
                (
                    await self._session.execute(
                        select(RIPEStatASNNeighbour).where(
                            RIPEStatASNNeighbour.asn == asn
                        )
                    )
                )
                .scalars()
                .all()
            )
            data = [
                ASNNeighbourRead(
                    neighbour_asn=r.neighbour_asn,
                    relationship=r.relationship,
                    power=r.power,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                query_value,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = await self._client.asn_neighbours(_asn_resource(asn))
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_asn_neighbours(raw, asn)

        await self._session.execute(
            delete(RIPEStatASNNeighbour).where(RIPEStatASNNeighbour.asn == asn)
        )
        now = utc_now()
        for n in parsed.neighbours:
            self._session.add(
                RIPEStatASNNeighbour(
                    asn=asn,
                    neighbour_asn=n.asn,
                    relationship=n.relationship,
                    power=n.power,
                    queried_at=now,
                )
            )
        await self._update_query_log(lookup_type, query_value, len(parsed.neighbours))
        await self._session.commit()

        data = [
            ASNNeighbourRead(
                neighbour_asn=n.asn,
                relationship=n.relationship,
                power=n.power,
            )
            for n in parsed.neighbours
        ]
        return self._to_result(lookup_type, query_value, data, len(parsed.neighbours))

    async def as_overview(
        self, raw_asn: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        asn = _normalize_asn(raw_asn)
        query_value = str(asn)
        lookup_type = RIPEStatLookupType.AS_OVERVIEW

        log = await self._get_query_log(lookup_type, query_value)
        if log and self._is_fresh(log):
            row = (
                await self._session.execute(
                    select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn)
                )
            ).scalar_one_or_none()
            if row:
                data = ASOverviewRead(
                    asn=row.asn,
                    holder=row.holder,
                    rir=row.rir,
                    announced=row.announced,
                    block_name=row.block_name,
                    block_resource=row.block_resource,
                )
                return self._to_result(
                    lookup_type,
                    query_value,
                    data,
                    1,
                    cached=True,
                    queried_at=log.queried_at,
                )

        if cached_only:
            return None

        try:
            raw = await self._client.as_overview(_asn_resource(asn))
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_as_overview(raw, asn)

        # upsert (unique on asn)
        existing = (
            await self._session.execute(
                select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn)
            )
        ).scalar_one_or_none()
        now = utc_now()
        if existing:
            existing.holder = parsed.holder
            existing.rir = parsed.rir
            existing.announced = parsed.announced
            existing.block_name = parsed.block_name
            existing.block_resource = parsed.block_resource
            existing.queried_at = now
            self._session.add(existing)
        else:
            self._session.add(
                RIPEStatASOverview(
                    asn=asn,
                    holder=parsed.holder,
                    rir=parsed.rir,
                    announced=parsed.announced,
                    block_name=parsed.block_name,
                    block_resource=parsed.block_resource,
                    queried_at=now,
                )
            )
        await self._update_query_log(lookup_type, query_value, 1)
        await self._session.commit()

        data = ASOverviewRead(
            asn=asn,
            holder=parsed.holder,
            rir=parsed.rir,
            announced=parsed.announced,
            block_name=parsed.block_name,
            block_resource=parsed.block_resource,
        )
        return self._to_result(lookup_type, query_value, data, 1)

    async def network_info(
        self, ip: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        ip = ip.strip()
        lookup_type = RIPEStatLookupType.NETWORK_INFO

        log = await self._get_query_log(lookup_type, ip)
        if log and self._is_fresh(log):
            rows = (
                (
                    await self._session.execute(
                        select(RIPEStatNetworkInfo).where(RIPEStatNetworkInfo.ip == ip)
                    )
                )
                .scalars()
                .all()
            )
            data = [NetworkInfoRead(ip=r.ip, prefix=r.prefix, asn=r.asn) for r in rows]
            return self._to_result(
                lookup_type,
                ip,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = await self._client.network_info(ip)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_network_info(raw, ip)

        await self._session.execute(
            delete(RIPEStatNetworkInfo).where(RIPEStatNetworkInfo.ip == ip)
        )
        now = utc_now()
        for asn_val in parsed.asns:
            self._session.add(
                RIPEStatNetworkInfo(
                    ip=ip,
                    prefix=parsed.prefix or "",
                    asn=asn_val,
                    queried_at=now,
                )
            )
        count = len(parsed.asns)
        await self._update_query_log(lookup_type, ip, count)
        await self._session.commit()

        data = [
            NetworkInfoRead(ip=ip, prefix=parsed.prefix or "", asn=a)
            for a in parsed.asns
        ]
        return self._to_result(lookup_type, ip, data, count)

    async def abuse_contact(
        self, resource: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        resource = resource.strip()
        lookup_type = RIPEStatLookupType.ABUSE_CONTACT

        log = await self._get_query_log(lookup_type, resource)
        if log and self._is_fresh(log):
            rows = (
                (
                    await self._session.execute(
                        select(RIPEStatAbuseContact).where(
                            RIPEStatAbuseContact.resource == resource
                        )
                    )
                )
                .scalars()
                .all()
            )
            emails = [r.abuse_email for r in rows]
            rir = rows[0].rir if rows else None
            data = AbuseContactRead(resource=resource, abuse_emails=emails, rir=rir)
            return self._to_result(
                lookup_type,
                resource,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = await self._client.abuse_contact(resource)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_abuse_contact(raw, resource)

        await self._session.execute(
            delete(RIPEStatAbuseContact).where(
                RIPEStatAbuseContact.resource == resource
            )
        )
        now = utc_now()
        for email in parsed.abuse_emails:
            self._session.add(
                RIPEStatAbuseContact(
                    resource=resource,
                    abuse_email=email,
                    rir=parsed.rir,
                    queried_at=now,
                )
            )
        await self._update_query_log(lookup_type, resource, len(parsed.abuse_emails))
        await self._session.commit()

        data = AbuseContactRead(
            resource=resource,
            abuse_emails=parsed.abuse_emails,
            rir=parsed.rir,
        )
        return self._to_result(lookup_type, resource, data, len(parsed.abuse_emails))

    async def prefix_overview(
        self, prefix: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        prefix = prefix.strip()
        lookup_type = RIPEStatLookupType.PREFIX_OVERVIEW

        log = await self._get_query_log(lookup_type, prefix)
        if log and self._is_fresh(log):
            rows = (
                (
                    await self._session.execute(
                        select(RIPEStatPrefixOverview).where(
                            RIPEStatPrefixOverview.prefix == prefix
                        )
                    )
                )
                .scalars()
                .all()
            )
            data = [
                PrefixOverviewRead(
                    prefix=r.prefix,
                    asn=r.asn,
                    holder=r.holder,
                    is_announced=r.is_announced,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                prefix,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = await self._client.prefix_overview(prefix)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_prefix_overview(raw, prefix)

        await self._session.execute(
            delete(RIPEStatPrefixOverview).where(
                RIPEStatPrefixOverview.prefix == prefix
            )
        )
        now = utc_now()
        for a in parsed.asns:
            self._session.add(
                RIPEStatPrefixOverview(
                    prefix=prefix,
                    asn=a.asn,
                    holder=a.holder,
                    is_announced=parsed.is_announced,
                    queried_at=now,
                )
            )
        await self._update_query_log(lookup_type, prefix, len(parsed.asns))
        await self._session.commit()

        data = [
            PrefixOverviewRead(
                prefix=prefix,
                asn=a.asn,
                holder=a.holder,
                is_announced=parsed.is_announced,
            )
            for a in parsed.asns
        ]
        return self._to_result(lookup_type, prefix, data, len(parsed.asns))

    async def related_prefixes(
        self, prefix: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        prefix = prefix.strip()
        lookup_type = RIPEStatLookupType.RELATED_PREFIXES

        log = await self._get_query_log(lookup_type, prefix)
        if log and self._is_fresh(log):
            rows = (
                (
                    await self._session.execute(
                        select(RIPEStatRelatedPrefix).where(
                            RIPEStatRelatedPrefix.prefix == prefix
                        )
                    )
                )
                .scalars()
                .all()
            )
            data = [
                RelatedPrefixRead(
                    related_prefix=r.related_prefix,
                    relationship=r.relationship,
                    origin_asn=r.origin_asn,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                prefix,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = await self._client.related_prefixes(prefix)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_related_prefixes(raw, prefix)

        await self._session.execute(
            delete(RIPEStatRelatedPrefix).where(RIPEStatRelatedPrefix.prefix == prefix)
        )
        now = utc_now()
        for r in parsed.related:
            self._session.add(
                RIPEStatRelatedPrefix(
                    prefix=prefix,
                    related_prefix=r.prefix,
                    relationship=r.relationship,
                    origin_asn=r.origin_asn,
                    queried_at=now,
                )
            )
        await self._update_query_log(lookup_type, prefix, len(parsed.related))
        await self._session.commit()

        data = [
            RelatedPrefixRead(
                related_prefix=r.prefix,
                relationship=r.relationship,
                origin_asn=r.origin_asn,
            )
            for r in parsed.related
        ]
        return self._to_result(lookup_type, prefix, data, len(parsed.related))

    # methods exposed to celery workers

    def announced_prefixes_sync(
        self, session: Session, raw_asn: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        asn = _normalize_asn(raw_asn)
        query_value = str(asn)
        lookup_type = RIPEStatLookupType.ANNOUNCED_PREFIXES

        log = self._get_query_log_sync(session, lookup_type, query_value)
        if log and self._is_fresh(log):
            rows = (
                session.execute(
                    select(RIPEStatAnnouncedPrefix).where(
                        RIPEStatAnnouncedPrefix.asn == asn
                    )
                )
                .scalars()
                .all()
            )
            data = [
                AnnouncedPrefixRead(
                    prefix=r.prefix,
                    ip_version=r.ip_version,
                    first_seen=r.first_seen,
                    last_seen=r.last_seen,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                query_value,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = self._client.announced_prefixes_sync(_asn_resource(asn))
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_announced_prefixes(raw, asn)

        session.execute(
            delete(RIPEStatAnnouncedPrefix).where(RIPEStatAnnouncedPrefix.asn == asn)
        )
        now = utc_now()
        for p in parsed.prefixes:
            session.add(
                RIPEStatAnnouncedPrefix(
                    asn=asn,
                    prefix=p.prefix,
                    ip_version=p.ip_version,
                    first_seen=p.first_seen,
                    last_seen=p.last_seen,
                    queried_at=now,
                )
            )
        self._update_query_log_sync(
            session, lookup_type, query_value, len(parsed.prefixes)
        )
        session.commit()

        data = [
            AnnouncedPrefixRead(
                prefix=p.prefix,
                ip_version=p.ip_version,
                first_seen=p.first_seen,
                last_seen=p.last_seen,
            )
            for p in parsed.prefixes
        ]
        return self._to_result(lookup_type, query_value, data, len(parsed.prefixes))

    def asn_neighbours_sync(
        self, session: Session, raw_asn: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        asn = _normalize_asn(raw_asn)
        query_value = str(asn)
        lookup_type = RIPEStatLookupType.ASN_NEIGHBOURS

        log = self._get_query_log_sync(session, lookup_type, query_value)
        if log and self._is_fresh(log):
            rows = (
                session.execute(
                    select(RIPEStatASNNeighbour).where(RIPEStatASNNeighbour.asn == asn)
                )
                .scalars()
                .all()
            )
            data = [
                ASNNeighbourRead(
                    neighbour_asn=r.neighbour_asn,
                    relationship=r.relationship,
                    power=r.power,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                query_value,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = self._client.asn_neighbours_sync(_asn_resource(asn))
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_asn_neighbours(raw, asn)

        session.execute(
            delete(RIPEStatASNNeighbour).where(RIPEStatASNNeighbour.asn == asn)
        )
        now = utc_now()
        for n in parsed.neighbours:
            session.add(
                RIPEStatASNNeighbour(
                    asn=asn,
                    neighbour_asn=n.asn,
                    relationship=n.relationship,
                    power=n.power,
                    queried_at=now,
                )
            )
        self._update_query_log_sync(
            session, lookup_type, query_value, len(parsed.neighbours)
        )
        session.commit()

        data = [
            ASNNeighbourRead(
                neighbour_asn=n.asn,
                relationship=n.relationship,
                power=n.power,
            )
            for n in parsed.neighbours
        ]
        return self._to_result(lookup_type, query_value, data, len(parsed.neighbours))

    def as_overview_sync(
        self, session: Session, raw_asn: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        asn = _normalize_asn(raw_asn)
        query_value = str(asn)
        lookup_type = RIPEStatLookupType.AS_OVERVIEW

        log = self._get_query_log_sync(session, lookup_type, query_value)
        if log and self._is_fresh(log):
            row = session.execute(
                select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn)
            ).scalar_one_or_none()
            if row:
                data = ASOverviewRead(
                    asn=row.asn,
                    holder=row.holder,
                    rir=row.rir,
                    announced=row.announced,
                    block_name=row.block_name,
                    block_resource=row.block_resource,
                )
                return self._to_result(
                    lookup_type,
                    query_value,
                    data,
                    1,
                    cached=True,
                    queried_at=log.queried_at,
                )

        if cached_only:
            return None

        try:
            raw = self._client.as_overview_sync(_asn_resource(asn))
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_as_overview(raw, asn)

        existing = session.execute(
            select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn)
        ).scalar_one_or_none()
        now = utc_now()
        if existing:
            existing.holder = parsed.holder
            existing.rir = parsed.rir
            existing.announced = parsed.announced
            existing.block_name = parsed.block_name
            existing.block_resource = parsed.block_resource
            existing.queried_at = now
            session.add(existing)
        else:
            session.add(
                RIPEStatASOverview(
                    asn=asn,
                    holder=parsed.holder,
                    rir=parsed.rir,
                    announced=parsed.announced,
                    block_name=parsed.block_name,
                    block_resource=parsed.block_resource,
                    queried_at=now,
                )
            )
        self._update_query_log_sync(session, lookup_type, query_value, 1)
        session.commit()

        data = ASOverviewRead(
            asn=asn,
            holder=parsed.holder,
            rir=parsed.rir,
            announced=parsed.announced,
            block_name=parsed.block_name,
            block_resource=parsed.block_resource,
        )
        return self._to_result(lookup_type, query_value, data, 1)

    def network_info_sync(
        self, session: Session, ip: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        ip = ip.strip()
        lookup_type = RIPEStatLookupType.NETWORK_INFO

        log = self._get_query_log_sync(session, lookup_type, ip)
        if log and self._is_fresh(log):
            rows = (
                session.execute(
                    select(RIPEStatNetworkInfo).where(RIPEStatNetworkInfo.ip == ip)
                )
                .scalars()
                .all()
            )
            data = [NetworkInfoRead(ip=r.ip, prefix=r.prefix, asn=r.asn) for r in rows]
            return self._to_result(
                lookup_type,
                ip,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = self._client.network_info_sync(ip)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_network_info(raw, ip)

        session.execute(delete(RIPEStatNetworkInfo).where(RIPEStatNetworkInfo.ip == ip))
        now = utc_now()
        for asn_val in parsed.asns:
            session.add(
                RIPEStatNetworkInfo(
                    ip=ip,
                    prefix=parsed.prefix or "",
                    asn=asn_val,
                    queried_at=now,
                )
            )
        count = len(parsed.asns)
        self._update_query_log_sync(session, lookup_type, ip, count)
        session.commit()

        data = [
            NetworkInfoRead(ip=ip, prefix=parsed.prefix or "", asn=a)
            for a in parsed.asns
        ]
        return self._to_result(lookup_type, ip, data, count)

    def abuse_contact_sync(
        self, session: Session, resource: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        resource = resource.strip()
        lookup_type = RIPEStatLookupType.ABUSE_CONTACT

        log = self._get_query_log_sync(session, lookup_type, resource)
        if log and self._is_fresh(log):
            rows = (
                session.execute(
                    select(RIPEStatAbuseContact).where(
                        RIPEStatAbuseContact.resource == resource
                    )
                )
                .scalars()
                .all()
            )
            emails = [r.abuse_email for r in rows]
            rir = rows[0].rir if rows else None
            data = AbuseContactRead(resource=resource, abuse_emails=emails, rir=rir)
            return self._to_result(
                lookup_type,
                resource,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = self._client.abuse_contact_sync(resource)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_abuse_contact(raw, resource)

        session.execute(
            delete(RIPEStatAbuseContact).where(
                RIPEStatAbuseContact.resource == resource
            )
        )
        now = utc_now()
        for email in parsed.abuse_emails:
            session.add(
                RIPEStatAbuseContact(
                    resource=resource,
                    abuse_email=email,
                    rir=parsed.rir,
                    queried_at=now,
                )
            )
        self._update_query_log_sync(
            session, lookup_type, resource, len(parsed.abuse_emails)
        )
        session.commit()

        data = AbuseContactRead(
            resource=resource,
            abuse_emails=parsed.abuse_emails,
            rir=parsed.rir,
        )
        return self._to_result(lookup_type, resource, data, len(parsed.abuse_emails))

    def prefix_overview_sync(
        self, session: Session, prefix: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        prefix = prefix.strip()
        lookup_type = RIPEStatLookupType.PREFIX_OVERVIEW

        log = self._get_query_log_sync(session, lookup_type, prefix)
        if log and self._is_fresh(log):
            rows = (
                session.execute(
                    select(RIPEStatPrefixOverview).where(
                        RIPEStatPrefixOverview.prefix == prefix
                    )
                )
                .scalars()
                .all()
            )
            data = [
                PrefixOverviewRead(
                    prefix=r.prefix,
                    asn=r.asn,
                    holder=r.holder,
                    is_announced=r.is_announced,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                prefix,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = self._client.prefix_overview_sync(prefix)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_prefix_overview(raw, prefix)

        session.execute(
            delete(RIPEStatPrefixOverview).where(
                RIPEStatPrefixOverview.prefix == prefix
            )
        )
        now = utc_now()
        for a in parsed.asns:
            session.add(
                RIPEStatPrefixOverview(
                    prefix=prefix,
                    asn=a.asn,
                    holder=a.holder,
                    is_announced=parsed.is_announced,
                    queried_at=now,
                )
            )
        self._update_query_log_sync(session, lookup_type, prefix, len(parsed.asns))
        session.commit()

        data = [
            PrefixOverviewRead(
                prefix=prefix,
                asn=a.asn,
                holder=a.holder,
                is_announced=parsed.is_announced,
            )
            for a in parsed.asns
        ]
        return self._to_result(lookup_type, prefix, data, len(parsed.asns))

    def related_prefixes_sync(
        self, session: Session, prefix: str, cached_only: bool = False
    ) -> RIPEStatResult | None:
        prefix = prefix.strip()
        lookup_type = RIPEStatLookupType.RELATED_PREFIXES

        log = self._get_query_log_sync(session, lookup_type, prefix)
        if log and self._is_fresh(log):
            rows = (
                session.execute(
                    select(RIPEStatRelatedPrefix).where(
                        RIPEStatRelatedPrefix.prefix == prefix
                    )
                )
                .scalars()
                .all()
            )
            data = [
                RelatedPrefixRead(
                    related_prefix=r.related_prefix,
                    relationship=r.relationship,
                    origin_asn=r.origin_asn,
                )
                for r in rows
            ]
            return self._to_result(
                lookup_type,
                prefix,
                data,
                log.result_count,
                cached=True,
                queried_at=log.queried_at,
            )

        if cached_only:
            return None

        try:
            raw = self._client.related_prefixes_sync(prefix)
        except RIPEStatAPIError as e:
            raise RIPEStatLookupError(str(e)) from e

        parsed = parse_related_prefixes(raw, prefix)

        session.execute(
            delete(RIPEStatRelatedPrefix).where(RIPEStatRelatedPrefix.prefix == prefix)
        )
        now = utc_now()
        for r in parsed.related:
            session.add(
                RIPEStatRelatedPrefix(
                    prefix=prefix,
                    related_prefix=r.prefix,
                    relationship=r.relationship,
                    origin_asn=r.origin_asn,
                    queried_at=now,
                )
            )
        self._update_query_log_sync(session, lookup_type, prefix, len(parsed.related))
        session.commit()

        data = [
            RelatedPrefixRead(
                related_prefix=r.prefix,
                relationship=r.relationship,
                origin_asn=r.origin_asn,
            )
            for r in parsed.related
        ]
        return self._to_result(lookup_type, prefix, data, len(parsed.related))
