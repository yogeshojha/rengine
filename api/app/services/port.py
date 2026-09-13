from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
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
    build_leads,
    build_service_groups,
    compile_service_query,
    parse_query,
    query_error_for,
)
from app.services.surface_scope import baselined_targets
from app.services.target_names import target_names
from shared.definitions.asset_query import COUNT_CAP, SERVICE_QUERY
from shared.definitions.ports import (
    DEFAULT_WEB_PORTS,
    PORT_SOURCE_LABELS,
    SERVICE_CLASS_LABELS,
    PortSource,
    ScanPolicy,
    ServiceClass,
    describe,
    service_label,
)
from shared.logging import get_logger
from shared.models.asset_query import QueryError, QueryGroups, QueryLeads
from shared.models.port import Port, PortRead, PortSummary
from shared.models.scan_correlation import (
    ExposureBand,
    ExposureLine,
    ScanExposure,
    ServiceFacets,
    ServiceFilter,
    ServicePage,
    ServiceRead,
)
from shared.models.subdomain import Facet
from shared.services.asset_query import lead_cache
from shared.services.surface_query import services as surface_services
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_HOSTS_PER_ROW = 20
_TOP_SERVICES = 8

_HOSTS_SQL = """
SELECT ip AS ip, s.name AS host
FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip
WHERE s.scan_id = ANY(:sids) AND ip = ANY(:ips)
"""

_SEEN_SQL = """
SELECT DISTINCT e.ip AS ip, e.number AS number
FROM ports e
JOIN ports cur ON cur.scan_id = ANY(:sids) AND cur.ip = e.ip AND cur.number = e.number
WHERE e.target_id = cur.target_id AND NOT (e.scan_id = ANY(:sids))
  AND e.discovered_at < cur.discovered_at AND e.ip = ANY(:ips)
"""


class PortService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_read(self, port: Port) -> PortRead:
        return PortRead(
            id=port.id,
            scan_id=port.scan_id,
            target_id=port.target_id,
            ip=port.ip,
            number=port.number,
            protocol=port.protocol,
            state=port.state,
            service_name=port.service_name,
            service_class=port.service_class,
            source=port.source,
            is_http=port.is_http,
            tls=port.tls,
            product=port.product,
            version=port.version,
            banner=port.banner,
            cpe=list(port.cpe or []),
            discovered_at=port.discovered_at,
        )

    def _conditions(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ) -> list:
        where = [Port.project_id == project_id]
        if scan_id is not None:
            where.append(Port.scan_id == scan_id)
        if target_id is not None:
            where.append(Port.target_id == target_id)
        if search:
            where.append(Port.ip.ilike(f"%{search}%"))
        return where

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ):
        return select(Port).where(
            *self._conditions(project_id, scan_id, target_id, search)
        )

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
        search: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[PortRead]:
        query = self._base_query(project_id, scan_id, target_id, search)
        query = query.order_by(Port.ip, Port.number).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_read(p) for p in result.scalars().all()]

    async def summary(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> PortSummary:
        name = func.coalesce(func.nullif(Port.service_name, ""), "unknown")
        rows = (
            await self.session.execute(
                select(name, func.count())
                .where(*self._conditions(project_id, scan_id, target_id, None))
                .group_by(name)
            )
        ).all()
        by_service = {str(service): int(count) for service, count in rows}
        return PortSummary(total=sum(by_service.values()), by_service=by_service)

    _derived = staticmethod(surface_services.derived)
    _apply_filter = staticmethod(surface_services.apply_filter)
    _order = staticmethod(surface_services.order)
    _scoped = staticmethod(surface_services.scoped)
    _context = staticmethod(surface_services.context)

    async def _seen_before(
        self, scope: QueryScope, ips: list[str]
    ) -> tuple[set[UUID], set[tuple[str, int]]]:
        baseline = await baselined_targets(self.session, Port, scope)
        if not baseline:
            return set(), set()
        rows = (
            await self.session.execute(
                text(_SEEN_SQL).bindparams(sids=list(scope.ids), ips=ips)
            )
        ).all()
        return baseline, {(ip, int(number)) for ip, number in rows}

    async def _hosts_for(
        self, scope: QueryScope, ips: list[str]
    ) -> dict[str, set[str]]:
        rows = (
            await self.session.execute(
                text(_HOSTS_SQL).bindparams(sids=list(scope.ids), ips=ips)
            )
        ).all()
        out: dict[str, set[str]] = {}
        for ip, host in rows:
            out.setdefault(ip, set()).add(host)
        return out

    async def search(self, scope: ScopeLike, f: ServiceFilter) -> ServicePage:
        scope = QueryScope.of(scope)
        now = utc_now()
        d, base = self._scoped(scope, f)
        try:
            predicate = compile_service_query(
                parse_query(f.q, SERVICE_QUERY), self._context(scope, d, now)
            )
        except QuerySyntaxError as exc:
            return ServicePage(
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
            logger.info("service query rejected by postgres", error=str(exc.orig))
            return ServicePage(error=rejected)

        total = int(counted or 0)
        capped = total > COUNT_CAP
        page = ServicePage(
            total=min(total, COUNT_CAP) if capped else total, total_capped=capped
        )
        if not rows:
            return page
        page_ips = [r["ip"] for r in rows]
        hosts = await self._hosts_for(scope, page_ips)
        baseline, seen = await self._seen_before(scope, page_ips)
        targets = await target_names(self.session, (r["target_id"] for r in rows))
        for r in rows:
            names = sorted(hosts.get(r["ip"], set()))
            description, registered = describe(int(r["port"]), r["service_name"])
            page.items.append(
                ServiceRead(
                    id=r["id"],
                    scan_id=r["scan_id"],
                    target_id=r["target_id"],
                    target_value=targets.get(r["target_id"]),
                    ip=r["ip"],
                    port=r["port"],
                    protocol=r["protocol"],
                    state=r["state"],
                    service_name=r["service_name"],
                    service_class=r["service_class"],
                    description=description,
                    registered=registered,
                    source=r["source"],
                    is_http=bool(r["is_http"]),
                    tls=bool(r["tls"]),
                    product=r["product"],
                    version=r["version_text"],
                    banner=r["banner"],
                    asn=r["asn"],
                    asn_org=r["asn_org"],
                    country=r["country"],
                    prefix=r["prefix"],
                    is_cdn=bool(r["is_cdn"]),
                    cdn_name=r["cdn_name"],
                    scan_policy=r["scan_policy"],
                    host_count=max(len(names), int(r["host_count"] or 0)),
                    hosts=names[:_HOSTS_PER_ROW],
                    web_count=int(r["web_count"] or 0),
                    status_code=r["status_code"],
                    url=r["url"],
                    title=r["title"],
                    screenshot_path=r["screenshot_path"],
                    is_sensitive=bool(r["sensitive"]),
                    is_new=r["target_id"] in baseline
                    and (r["ip"], int(r["port"])) not in seen,
                )
            )
        return page

    async def seeds(
        self, scope: ScopeLike, f: ServiceFilter, limit: int
    ) -> list[tuple[str, UUID]]:
        scope = QueryScope.of(scope)
        now = utc_now()
        d, base = self._scoped(scope, f, columns=lambda d: (d.c.ip, d.c.scan_id))
        try:
            predicate = compile_service_query(
                parse_query(f.q, SERVICE_QUERY), self._context(scope, d, now)
            )
        except QuerySyntaxError:
            return []
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        rows = await self.session.execute(base.distinct().limit(limit))
        return [(ip, scan_id) for ip, scan_id in rows.all()]

    async def leads(self, scope: ScopeLike, f: ServiceFilter) -> QueryLeads:
        scope = QueryScope.of(scope)

        async def _build() -> QueryLeads:
            now = utc_now()
            d, base = self._scoped(scope, f, columns=lambda d: (d.c.id,))
            ctx = self._context(scope, d, now)
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            try:
                return await build_leads(
                    self.session,
                    base,
                    SERVICE_QUERY.examples,
                    lambda q: compile_service_query(parse_query(q, SERVICE_QUERY), ctx),
                    filtered=f.has_facets(),
                )
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("service leads failed", error=str(exc.orig))
                return QueryLeads()

        return await lead_cache.leads(
            self.session,
            dimension="services",
            scans=scope.ids,
            facets=lead_cache.facets_of(f),
            build=_build,
        )

    async def groups(self, scope: ScopeLike, f: ServiceFilter, key: str) -> QueryGroups:
        scope = QueryScope.of(scope)
        now = utc_now()
        d, base = self._scoped(scope, f)
        try:
            predicate = compile_service_query(
                parse_query(f.q, SERVICE_QUERY), self._context(scope, d, now)
            )
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            return await build_service_groups(self.session, base, key)
        except DBAPIError as exc:
            await self.session.rollback()
            logger.info("service groups failed", error=str(exc.orig))
            return QueryGroups(dimension=key)

    async def facets(self, scope: ScopeLike) -> ServiceFacets:
        scope = QueryScope.of(scope)
        d = self._derived(scope)
        n = func.count()

        async def tally(col, limit: int = _FACET_LIMIT):
            rows = await self.session.execute(
                select(col, n)
                .select_from(d)
                .where(col.isnot(None))
                .group_by(col)
                .order_by(n.desc())
                .limit(limit)
            )
            return rows.all()

        class_rows = await tally(d.c.service_class, len(SERVICE_CLASS_LABELS))
        port_rows = await tally(d.c.port)
        service_rows = await tally(d.c.service_name)
        source_rows = await tally(d.c.source, len(PORT_SOURCE_LABELS))
        asn_rows = await self.session.execute(
            select(d.c.asn, func.max(d.c.asn_org), n)
            .where(d.c.asn.isnot(None))
            .group_by(d.c.asn)
            .order_by(n.desc())
            .limit(_FACET_LIMIT)
        )
        country_rows = await tally(d.c.country)
        return ServiceFacets(
            klass=[
                Facet(
                    value=str(value),
                    label=SERVICE_CLASS_LABELS.get(str(value), str(value)),
                    count=int(c),
                )
                for value, c in class_rows
            ],
            port=[
                Facet(value=str(value), label=str(value), count=int(c))
                for value, c in port_rows
            ],
            service=[
                Facet(value=str(value), label=service_label(str(value)), count=int(c))
                for value, c in service_rows
            ],
            source=[
                Facet(
                    value=str(value),
                    label=PORT_SOURCE_LABELS.get(str(value), str(value)),
                    count=int(c),
                )
                for value, c in source_rows
            ],
            asn=[
                Facet(
                    value=str(asn),
                    label=f"AS{asn} · {org}" if org else f"AS{asn}",
                    count=int(c),
                )
                for asn, org, c in asn_rows.all()
            ],
            country=[
                Facet(value=str(value), label=str(value), count=int(c))
                for value, c in country_rows
            ],
        )

    async def exposure(self, scope: ScopeLike) -> ScanExposure:
        scope = QueryScope.of(scope)
        d = self._derived(scope)
        n = func.count()
        addresses = func.count(func.distinct(d.c.ip))
        web_class = d.c.service_class == ServiceClass.WEB.value
        answering = d.c.is_http.is_(True)
        standard = d.c.port.in_(DEFAULT_WEB_PORTS)
        totals = (
            await self.session.execute(
                select(
                    n.label("services"),
                    addresses.label("addresses"),
                    n.filter(web_class).label("web"),
                    n.filter(~web_class).label("non_web"),
                    n.filter(answering).label("answering"),
                    n.filter(d.c.sensitive.is_(True)).label("sensitive"),
                    n.filter(d.c.product.isnot(None)).label("named"),
                    n.filter(d.c.source == PortSource.INTERNETDB.value).label(
                        "passive"
                    ),
                    n.filter(answering & ~standard).label("nonstandard"),
                ).select_from(d)
            )
        ).one()

        band_rows = (
            await self.session.execute(
                select(d.c.service_class, n, addresses)
                .select_from(d)
                .group_by(d.c.service_class)
            )
        ).all()
        by_class = {str(k): (int(c), int(a)) for k, c, a in band_rows}
        bands = [
            ExposureBand(
                key=key,
                label=label,
                count=by_class.get(key, (0, 0))[0],
                addresses=by_class.get(key, (0, 0))[1],
                query=f"class:{key}",
            )
            for key, label in SERVICE_CLASS_LABELS.items()
        ]

        service_rows = (
            await self.session.execute(
                select(d.c.service_name, n, addresses)
                .select_from(d)
                .where(d.c.service_name.isnot(None))
                .group_by(d.c.service_name)
                .order_by(n.desc())
                .limit(_TOP_SERVICES)
            )
        ).all()
        top_services = [
            ExposureLine(
                key=str(name),
                label=service_label(str(name)),
                detail=f"{int(addr)} address{'es' if int(addr) != 1 else ''}",
                count=int(c),
                query=f"service={name}",
            )
            for name, c, addr in service_rows
        ]

        policy_rows = (
            await self.session.execute(
                text(
                    "SELECT coalesce(scan_policy, 'unplanned') AS policy, "
                    "coalesce(scan_policy_reason, '') AS reason, count(*) AS n "
                    "FROM ip_addresses WHERE scan_id = ANY(:sids) GROUP BY 1, 2"
                ).bindparams(sids=list(scope.ids))
            )
        ).all()
        coverage = _coverage(policy_rows)
        scanned = sum(
            int(c)
            for policy, _reason, c in policy_rows
            if policy in (ScanPolicy.FULL.value, ScanPolicy.WEB.value)
        )
        return ScanExposure(
            services=int(totals.services or 0),
            addresses=int(totals.addresses or 0),
            web_services=int(totals.web or 0),
            non_web_services=int(totals.non_web or 0),
            answering_http=int(totals.answering or 0),
            sensitive=int(totals.sensitive or 0),
            named=int(totals.named or 0),
            passive_only=int(totals.passive or 0),
            nonstandard_web=int(totals.nonstandard or 0),
            bands=bands,
            top_services=top_services,
            coverage=coverage,
            scanned=scanned,
        )


_COVERAGE_LABELS: dict[str, tuple[str, str]] = {
    ScanPolicy.FULL.value: ("Scanned in full", ""),
    ScanPolicy.WEB.value: ("Web ports only", ""),
    ScanPolicy.SKIP.value: ("Not scanned", ""),
    "unplanned": ("Not reached", ""),
}
_COVERAGE_REASONS: dict[str, str] = {
    "cdn": "CDN-fronted",
    "cloud": "Cloud provider",
    "scope": "Excluded by scope",
    "private": "Private address",
    "unreachable": "No response",
}


def _coverage(rows) -> list[ExposureLine]:
    merged: dict[tuple[str, str], int] = {}
    for policy, reason, count in rows:
        merged[(str(policy), str(reason or ""))] = merged.get(
            (str(policy), str(reason or "")), 0
        ) + int(count)
    out: list[ExposureLine] = []
    for (policy, reason), count in merged.items():
        label, query = _COVERAGE_LABELS.get(policy, (policy, ""))
        out.append(
            ExposureLine(
                key=f"{policy}:{reason}" if reason else policy,
                label=label,
                detail=_COVERAGE_REASONS.get(reason) or None,
                count=count,
                query=query,
            )
        )
    out.sort(key=lambda line: -line.count)
    return out
