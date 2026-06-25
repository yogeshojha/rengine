from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.ip_address import IpAddress, IpAddressRead, IpAddressSummary


class IpAddressService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_read(self, ip: IpAddress) -> IpAddressRead:
        return IpAddressRead(
            id=ip.id,
            scan_id=ip.scan_id,
            target_id=ip.target_id,
            ip=ip.ip,
            version=ip.version,
            source=ip.source,
            ptr_hostnames=list(ip.ptr_hostnames or []),
            asn=ip.asn,
            asn_org=ip.asn_org,
            prefix=ip.prefix,
            country=ip.country,
            is_cdn=ip.is_cdn,
            cdn_name=ip.cdn_name,
            is_alive=ip.is_alive,
            discovered_at=ip.discovered_at,
        )

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ):
        query = select(IpAddress).where(IpAddress.project_id == project_id)
        if scan_id is not None:
            query = query.where(IpAddress.scan_id == scan_id)
        if target_id is not None:
            query = query.where(IpAddress.target_id == target_id)
        if search:
            query = query.where(IpAddress.ip.ilike(f"%{search}%"))
        return query

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
        search: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[IpAddressRead]:
        query = self._base_query(project_id, scan_id, target_id, search)
        query = query.order_by(IpAddress.ip).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_read(ip) for ip in result.scalars().all()]

    async def summary(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> IpAddressSummary:
        query = self._base_query(project_id, scan_id, target_id, None)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        by_source: Counter = Counter()
        alive = 0
        cdn = 0
        for row in rows:
            by_source[row.source] += 1
            if row.is_alive:
                alive += 1
            if row.is_cdn:
                cdn += 1
        return IpAddressSummary(
            total=len(rows), alive=alive, cdn=cdn, by_source=dict(by_source)
        )
