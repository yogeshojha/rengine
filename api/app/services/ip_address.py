from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    distinct,
    func,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    build_ip_groups,
    build_leads,
    compile_ip_query,
    parse_query,
    query_error_for,
)
from app.services.port import PortService
from app.services.target_names import target_names
from shared.definitions.asset_query import COUNT_CAP, IP_EXPOSURE, IP_QUERY
from shared.definitions.ports import port_interest
from shared.logging import get_logger
from shared.models.asset_query import QueryError, QueryGroups, QueryLeads
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress, IpAddressRead, IpAddressSummary
from shared.models.port import Port
from shared.models.scan_correlation import (
    IpFacets,
    IpGroupFilter,
    IpGroupPage,
    IpGroupRead,
)
from shared.models.subdomain import Facet
from shared.services.asset_query import lead_cache
from shared.services.surface_query import ips as surface_ips
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_HOSTS_PER_ROW = 50


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

    def _filters(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ) -> list:
        conditions = [IpAddress.project_id == project_id]
        if scan_id is not None:
            conditions.append(IpAddress.scan_id == scan_id)
        if target_id is not None:
            conditions.append(IpAddress.target_id == target_id)
        if search:
            conditions.append(IpAddress.ip.ilike(f"%{search}%"))
        return conditions

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ):
        return select(IpAddress).where(
            *self._filters(project_id, scan_id, target_id, search)
        )

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
        where = self._filters(project_id, scan_id, target_id, None)
        totals = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(IpAddress.is_alive.is_(True)),
                    func.count().filter(IpAddress.is_cdn.is_(True)),
                ).where(*where)
            )
        ).one()
        by_source = (
            await self.session.execute(
                select(IpAddress.source, func.count())
                .where(*where)
                .group_by(IpAddress.source)
            )
        ).all()
        return IpAddressSummary(
            total=int(totals[0] or 0),
            alive=int(totals[1] or 0),
            cdn=int(totals[2] or 0),
            by_source={str(source): int(n) for source, n in by_source},
        )

    async def _page_details(
        self, scope: QueryScope, page_ips: list[str]
    ) -> tuple[dict[str, list], dict[str, set]]:
        ps = PortService(self.session)
        port_rows = (
            (
                await self.session.execute(
                    select(Port)
                    .where(scope.match(Port.scan_id), Port.ip.in_(page_ips))
                    .order_by(Port.number)
                )
            )
            .scalars()
            .all()
        )
        ports_by_ip: dict[str, list] = {}
        for p in sorted(port_rows, key=lambda r: (port_interest(r.number), r.number)):
            ports_by_ip.setdefault(p.ip, []).append(ps._to_read(p))

        host_rows = (
            await self.session.execute(
                text(
                    "SELECT ip AS ip, s.name AS host "
                    "FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip "
                    "WHERE s.scan_id = ANY(:sids) AND ip = ANY(:ips)"
                ).bindparams(sids=list(scope.ids), ips=page_ips)
            )
        ).all()
        asset_rows = (
            await self.session.execute(
                select(HttpAsset.ip, HttpAsset.host).where(
                    scope.match(HttpAsset.scan_id), HttpAsset.ip.in_(page_ips)
                )
            )
        ).all()
        hosts_by_ip: dict[str, set] = {}
        for ip, host in host_rows:
            hosts_by_ip.setdefault(ip, set()).add(host)
        for ip, host in asset_rows:
            if ip:
                hosts_by_ip.setdefault(ip, set()).add(host)
        return ports_by_ip, hosts_by_ip

    _derived = staticmethod(surface_ips.derived)
    _exposure = staticmethod(surface_ips.exposure_bucket)
    _port_exists = staticmethod(surface_ips.port_exists)
    _apply_filter = staticmethod(surface_ips.apply_filter)
    _order = staticmethod(surface_ips.order)
    _scoped = staticmethod(surface_ips.scoped)
    _context = staticmethod(surface_ips.context)

    async def search(self, scope: ScopeLike, f: IpGroupFilter) -> IpGroupPage:
        scope = QueryScope.of(scope)
        now = utc_now()
        d, base = self._scoped(scope, f)
        try:
            predicate = compile_ip_query(
                parse_query(f.q, IP_QUERY), self._context(scope, d, now)
            )
        except QuerySyntaxError as exc:
            return IpGroupPage(
                error=QueryError(
                    message=exc.message, hint=exc.hint, start=exc.start, end=exc.end
                )
            )
        if predicate is not None:
            base = base.where(predicate)

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            counted = await self.session.scalar(
                select(func.count()).select_from(base.limit(COUNT_CAP + 1).subquery())
            )
            rows = (
                (
                    await self.session.execute(
                        self._order(base, d, f).limit(f.limit).offset(f.offset)
                    )
                )
                .mappings()
                .all()
            )
        except DBAPIError as exc:
            await self.session.rollback()
            rejected = query_error_for(exc)
            if rejected is None:
                raise
            logger.info("address query rejected by postgres", error=str(exc.orig))
            return IpGroupPage(error=rejected)

        total = int(counted or 0)
        capped = total > COUNT_CAP
        page = IpGroupPage(
            total=min(total, COUNT_CAP) if capped else total, total_capped=capped
        )
        page_ips = [r["ip"] for r in rows]
        if not page_ips:
            return page
        ports_by_ip, hosts_by_ip = await self._page_details(scope, page_ips)
        names = await target_names(
            self.session, (tid for r in rows for tid in (r["target_ids"] or []))
        )
        for r in rows:
            host_set = hosts_by_ip.get(r["ip"], set())
            page.items.append(
                IpGroupRead(
                    ip=r["ip"],
                    version=r["version"],
                    targets=sorted(
                        names[tid] for tid in (r["target_ids"] or []) if tid in names
                    ),
                    asn=r["asn"],
                    asn_org=r["asn_org"],
                    country=r["country"],
                    prefix=r["prefix"],
                    is_cdn=bool(r["is_cdn"]),
                    cdn_name=r["cdn_name"],
                    is_alive=r["is_alive"],
                    ptr_hostnames=list(r["ptr_hostnames"] or []),
                    ports=ports_by_ip.get(r["ip"], []),
                    host_count=max(len(host_set), int(r["host_count"] or 0)),
                    hosts=sorted(host_set)[:_HOSTS_PER_ROW],
                    port_count=int(r["port_count"] or 0),
                    has_sensitive=bool(r["sensitive"]),
                    asset_count=int(r["asset_count"] or 0),
                )
            )
        return page

    async def seeds(
        self, scope: ScopeLike, f: IpGroupFilter, limit: int
    ) -> list[tuple[str, list[UUID]]]:
        """An address folds across every target that serves it."""
        scope = QueryScope.of(scope)
        now = utc_now()
        d, base = self._scoped(scope, f, columns=lambda d: (d.c.ip, d.c.target_ids))
        try:
            predicate = compile_ip_query(
                parse_query(f.q, IP_QUERY), self._context(scope, d, now)
            )
        except QuerySyntaxError:
            return []
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        rows = await self.session.execute(base.order_by(d.c.ip).limit(limit))
        return [(ip, list(target_ids or [])) for ip, target_ids in rows.all()]

    async def leads(self, scope: ScopeLike, f: IpGroupFilter) -> QueryLeads:
        scope = QueryScope.of(scope)

        async def _build() -> QueryLeads:
            now = utc_now()
            d, base = self._scoped(scope, f, columns=lambda d: (d.c.ip,))
            ctx = self._context(scope, d, now)
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            try:
                return await build_leads(
                    self.session,
                    base,
                    IP_QUERY.examples,
                    lambda q: compile_ip_query(parse_query(q, IP_QUERY), ctx),
                    filtered=f.has_facets(),
                )
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("address leads failed", error=str(exc.orig))
                return QueryLeads()

        return await lead_cache.leads(
            self.session,
            dimension="ips",
            scans=scope.ids,
            facets=lead_cache.facets_of(f),
            build=_build,
        )

    async def groups(self, scope: ScopeLike, f: IpGroupFilter, key: str) -> QueryGroups:
        scope = QueryScope.of(scope)
        now = utc_now()
        d, base = self._scoped(scope, f)
        try:
            predicate = compile_ip_query(
                parse_query(f.q, IP_QUERY), self._context(scope, d, now)
            )
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            return await build_ip_groups(self.session, base, key, scope)
        except DBAPIError as exc:
            await self.session.rollback()
            logger.info("address groups failed", error=str(exc.orig))
            return QueryGroups(dimension=key)

    async def facets(self, scope: ScopeLike) -> IpFacets:
        scope = QueryScope.of(scope)
        d = self._derived(scope)
        n = func.count()
        exposure_rows = (
            await self.session.execute(
                select(
                    *[
                        func.count().filter(self._exposure(d, bucket)).label(bucket)
                        for bucket in IP_EXPOSURE
                    ]
                ).select_from(d)
            )
        ).one()
        asn_rows = (
            await self.session.execute(
                select(d.c.asn, func.max(d.c.asn_org), n)
                .where(d.c.asn.isnot(None))
                .group_by(d.c.asn)
                .order_by(n.desc())
                .limit(_FACET_LIMIT)
            )
        ).all()
        country_rows = (
            await self.session.execute(
                select(d.c.country, n)
                .where(d.c.country.isnot(None))
                .group_by(d.c.country)
                .order_by(n.desc())
                .limit(_FACET_LIMIT)
            )
        ).all()
        ips = func.count(distinct(Port.ip))
        port_rows = (
            await self.session.execute(
                select(Port.number, func.max(Port.service_name), ips)
                .where(scope.match(Port.scan_id))
                .group_by(Port.number)
                .order_by(ips.desc())
                .limit(_FACET_LIMIT)
            )
        ).all()
        service_rows = (
            await self.session.execute(
                select(Port.service_name, ips)
                .where(scope.match(Port.scan_id), Port.service_name.isnot(None))
                .group_by(Port.service_name)
                .order_by(ips.desc())
                .limit(_FACET_LIMIT)
            )
        ).all()
        return IpFacets(
            exposure=[
                Facet(value=bucket, label=label, count=int(exposure_rows[index]))
                for index, (bucket, label) in enumerate(IP_EXPOSURE.items())
            ],
            asn=[
                Facet(
                    value=str(asn),
                    label=f"AS{asn} · {org}" if org else f"AS{asn}",
                    count=int(c),
                )
                for asn, org, c in asn_rows
            ],
            country=[
                Facet(value=str(cc), label=str(cc), count=int(c))
                for cc, c in country_rows
            ],
            port=[
                Facet(
                    value=str(num),
                    label=f"{num} · {svc}" if svc else str(num),
                    count=int(c),
                )
                for num, svc, c in port_rows
            ],
            service=[
                Facet(value=str(svc), label=str(svc), count=int(c))
                for svc, c in service_rows
            ],
        )
