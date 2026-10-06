from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    distinct,
    func,
    select,
    text,
    tuple_,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.port import PortService
from app.services.target_names import target_names
from shared.definitions.asset_query import ALL_TAB, COUNT_CAP, IP_EXPOSURE, IP_QUERY
from shared.definitions.ports import port_interest
from shared.logging import get_logger
from shared.models.asset_query import QueryCounts, QueryGroups, QueryLeads
from shared.models.ip_address import IpAddress, IpAddressRead
from shared.models.port import Port
from shared.models.scan_correlation import (
    IpFacets,
    IpGroupFilter,
    IpGroupPage,
    IpGroupRead,
)
from shared.models.subdomain import Facet
from shared.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    build_ip_groups,
    build_leads,
    compile_ip_query,
    count_named,
    count_queries,
    lead_cache,
    page_rows,
    parse_query,
    query_error_for,
    syntax_error,
)
from shared.services.surface_query import ips as surface_ips
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_HOSTS_PER_ROW = 50
# grouping(asn, country) per grouping set
_BY_ASN = 1
_BY_COUNTRY = 2
_BY_NOTHING = 3


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

        hosts_by_ip = await ps.hosts_for(scope, page_ips)
        return ports_by_ip, hosts_by_ip

    _derived = staticmethod(surface_ips.derived)
    _exposure = staticmethod(surface_ips.exposure_bucket)
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
            return IpGroupPage(error=syntax_error(exc))
        if predicate is not None:
            base = base.where(predicate)

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            rows, counted = await page_rows(
                self.session,
                base,
                lambda q: self._order(q, d, f),
                limit=f.limit,
                offset=f.offset,
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
                    host_count=int(r["host_count"] or 0),
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

    async def tabs(self, scope: ScopeLike, f: IpGroupFilter) -> QueryCounts:
        """Addresses under each exposure tab, for the filter without its own exposure."""
        scope = QueryScope.of(scope)
        f = f.model_copy(update={"exposure": []})

        async def _build() -> QueryCounts:
            now = utc_now()
            d, base = self._scoped(scope, f, columns=lambda d: (d.c.ip,))
            try:
                predicate = compile_ip_query(
                    parse_query(f.q, IP_QUERY), self._context(scope, d, now)
                )
            except QuerySyntaxError:
                return QueryCounts()
            if predicate is not None:
                base = base.where(predicate)
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            tabs = {k: self._exposure(d, k) for k in IP_EXPOSURE}
            try:
                return await count_named(self.session, base, {ALL_TAB: None, **tabs})
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("address tabs failed", error=str(exc.orig))
                return QueryCounts()

        return await lead_cache.cached(
            self.session,
            name="tabs:ips",
            scans=scope.ids,
            facets=lead_cache.filter_of(f),
            model=QueryCounts,
            build=_build,
            keep=lambda counted: counted.computed,
            ttl=lead_cache.SEARCH_TTL_SECONDS,
            live_ttl=None,
        )

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

    async def counts(self, scope: ScopeLike, queries: list[str]) -> QueryCounts:
        """Addresses each query selects in the scope, one statement."""
        scope = QueryScope.of(scope)
        f = IpGroupFilter()

        async def _build() -> QueryCounts:
            d, base = self._scoped(scope, f, columns=lambda d: (d.c.ip,))
            ctx = self._context(scope, d, utc_now())
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            try:
                return await count_queries(
                    self.session,
                    base,
                    queries,
                    lambda q: compile_ip_query(parse_query(q, IP_QUERY), ctx),
                )
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("address counts failed", error=str(exc.orig))
                return QueryCounts()

        return await lead_cache.cached(
            self.session,
            name="counts:ips",
            scans=scope.ids,
            facets="|".join(queries),
            model=QueryCounts,
            build=_build,
            keep=lambda computed: computed.computed,
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
        grouped = (
            await self.session.execute(
                select(
                    func.grouping(d.c.asn, d.c.country),
                    d.c.asn,
                    d.c.country,
                    func.max(d.c.asn_org),
                    n,
                    *[func.count().filter(self._exposure(d, b)) for b in IP_EXPOSURE],
                ).group_by(
                    func.grouping_sets(tuple_(d.c.asn), tuple_(d.c.country), tuple_())
                )
            )
        ).all()
        exposure_rows: tuple = (0,) * len(IP_EXPOSURE)
        asn_rows: list[tuple] = []
        country_rows: list[tuple] = []
        for grouping, asn, country, org, count, *exposure in grouped:
            if grouping == _BY_ASN and asn is not None:
                asn_rows.append((asn, org, count))
            elif grouping == _BY_COUNTRY and country is not None:
                country_rows.append((country, count))
            elif grouping == _BY_NOTHING:
                exposure_rows = tuple(exposure)
        asn_rows = sorted(asn_rows, key=lambda r: (-r[2], r[0]))[:_FACET_LIMIT]
        country_rows = sorted(country_rows, key=lambda r: (-r[1], r[0]))[:_FACET_LIMIT]
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
