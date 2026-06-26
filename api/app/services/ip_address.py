from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import Text, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.port import PortService
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress, IpAddressRead, IpAddressSummary
from shared.models.port import Port
from shared.models.scan_correlation import IpGroupPage, IpGroupRead


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

    async def groups(
        self,
        project_id: UUID,
        scan_id: UUID,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> IpGroupPage:
        base = select(IpAddress).where(
            IpAddress.project_id == project_id, IpAddress.scan_id == scan_id
        )
        if search:
            like = f"%{search}%"
            base = base.where(
                or_(
                    IpAddress.ip.ilike(like),
                    IpAddress.asn_org.ilike(like),
                    cast(IpAddress.ptr_hostnames, Text).ilike(like),
                )
            )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(IpAddress.ip).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        page_ips = [r.ip for r in rows]
        if not page_ips:
            return IpGroupPage(items=[], total=int(total or 0))

        ps = PortService(self.session)
        port_rows = (
            (
                await self.session.execute(
                    select(Port)
                    .where(Port.scan_id == scan_id, Port.ip.in_(page_ips))
                    .order_by(Port.number)
                )
            )
            .scalars()
            .all()
        )
        ports_by_ip: dict[str, list] = {}
        for p in port_rows:
            ports_by_ip.setdefault(p.ip, []).append(ps._to_read(p))

        host_rows = (
            await self.session.execute(
                text(
                    "SELECT ip AS ip, s.name AS host "
                    "FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip "
                    "WHERE s.scan_id = :sid AND ip = ANY(:ips)"
                ).bindparams(sid=scan_id, ips=page_ips)
            )
        ).all()
        asset_rows = (
            await self.session.execute(
                select(HttpAsset.ip, HttpAsset.host).where(
                    HttpAsset.scan_id == scan_id, HttpAsset.ip.in_(page_ips)
                )
            )
        ).all()
        hosts_by_ip: dict[str, set] = {}
        for ip, host in host_rows:
            hosts_by_ip.setdefault(ip, set()).add(host)
        for ip, host in asset_rows:
            if ip:
                hosts_by_ip.setdefault(ip, set()).add(host)

        items = []
        for r in rows:
            host_set = hosts_by_ip.get(r.ip, set())
            items.append(
                IpGroupRead(
                    ip=r.ip,
                    version=r.version,
                    asn=r.asn,
                    asn_org=r.asn_org,
                    country=r.country,
                    prefix=r.prefix,
                    is_cdn=r.is_cdn,
                    cdn_name=r.cdn_name,
                    is_alive=r.is_alive,
                    ptr_hostnames=list(r.ptr_hostnames or []),
                    ports=ports_by_ip.get(r.ip, []),
                    host_count=len(host_set),
                    hosts=sorted(host_set)[:50],
                )
            )
        return IpGroupPage(items=items, total=int(total or 0))
