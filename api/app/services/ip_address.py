from __future__ import annotations

from collections import Counter
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Integer,
    String,
    and_,
    bindparam,
    cast,
    column,
    distinct,
    exists,
    func,
    not_,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import (
    STATEMENT_TIMEOUT,
    IpQueryContext,
    QuerySyntaxError,
    build_ip_groups,
    build_leads,
    compile_ip_query,
    parse_query,
    query_error_for,
)
from app.services.port import PortService
from shared.definitions.asset_query import COUNT_CAP, IP_EXPOSURE, IP_QUERY
from shared.definitions.ports import SENSITIVE_PORTS
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
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_HOSTS_PER_ROW = 50

# every IP the scan touched (resolved names, probed assets, open ports, enrichment rows)
_DERIVED_SQL = """
WITH hosts AS (
    SELECT ip, count(DISTINCT s.name) AS host_count
    FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip
    WHERE s.scan_id = :sid GROUP BY ip
), open_ports AS (
    SELECT ip, count(*) AS port_count, bool_or(number = ANY(:sensitive_ports)) AS sensitive
    FROM ports WHERE scan_id = :sid GROUP BY ip
), assets AS (
    SELECT ip, max(asn) AS asn, max(asn_org) AS asn_org, bool_or(is_cdn) AS is_cdn,
           max(cdn_name) AS cdn_name, count(*) AS asset_count
    FROM http_assets WHERE scan_id = :sid AND ip IS NOT NULL GROUP BY ip
), ips AS (
    SELECT ip FROM hosts UNION SELECT ip FROM open_ports UNION SELECT ip FROM assets
    UNION SELECT ip FROM ip_addresses WHERE scan_id = :sid
)
SELECT i.ip AS ip,
       CASE WHEN i.ip LIKE '%:%' THEN 6 ELSE 4 END AS version,
       coalesce(x.asn, a.asn) AS asn,
       coalesce(x.asn_org, a.asn_org) AS asn_org,
       x.country AS country,
       x.prefix AS prefix,
       coalesce(x.is_cdn, a.is_cdn, false) AS is_cdn,
       coalesce(x.cdn_name, a.cdn_name) AS cdn_name,
       coalesce(x.is_alive, a.asset_count > 0 OR p.port_count > 0, false) AS is_alive,
       coalesce(cast(x.ptr_hostnames AS jsonb), '[]'::jsonb) AS ptr_hostnames,
       coalesce(h.host_count, 0) AS host_count,
       coalesce(p.port_count, 0) AS port_count,
       coalesce(p.sensitive, false) AS sensitive,
       coalesce(a.asset_count, 0) AS asset_count
FROM ips i
LEFT JOIN hosts h ON h.ip = i.ip
LEFT JOIN open_ports p ON p.ip = i.ip
LEFT JOIN assets a ON a.ip = i.ip
LEFT JOIN ip_addresses x ON x.scan_id = :sid AND x.ip = i.ip
"""


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

    async def _page_details(
        self, scan_id: UUID, page_ips: list[str]
    ) -> tuple[dict[str, list], dict[str, set]]:
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
        return ports_by_ip, hosts_by_ip

    @staticmethod
    def _derived(scan_id: UUID):
        return (
            text(_DERIVED_SQL)
            .columns(
                column("ip", String),
                column("version", Integer),
                column("asn", Integer),
                column("asn_org", String),
                column("country", String),
                column("prefix", String),
                column("is_cdn", Boolean),
                column("cdn_name", String),
                column("is_alive", Boolean),
                column("ptr_hostnames", JSONB),
                column("host_count", Integer),
                column("port_count", Integer),
                column("sensitive", Boolean),
                column("asset_count", Integer),
            )
            .bindparams(
                bindparam("sid", scan_id),
                bindparam("sensitive_ports", SENSITIVE_PORTS, type_=ARRAY(Integer)),
            )
            .subquery("ip_groups")
        )

    @staticmethod
    def _port_exists(scan_id: UUID, d, cond):
        return exists(select(1).where(Port.scan_id == scan_id, Port.ip == d.c.ip, cond))

    @staticmethod
    def _exposure(d, bucket: str):
        if bucket == "open":
            return d.c.port_count > 0
        alive = d.c.is_alive.is_(True)
        if bucket == "responding":
            return and_(d.c.port_count == 0, alive)
        if bucket == "quiet":
            return and_(d.c.port_count == 0, not_(alive))
        return None

    def _apply_filter(self, q, d, f: IpGroupFilter, scan_id: UUID):
        if f.exposure:
            buckets = [self._exposure(d, b) for b in f.exposure]
            q = q.where(or_(*[b for b in buckets if b is not None]))
        if f.asns:
            q = q.where(d.c.asn.in_(f.asns))
        if f.countries:
            q = q.where(d.c.country.in_(f.countries))
        if f.ports:
            q = q.where(self._port_exists(scan_id, d, Port.number.in_(f.ports)))
        if f.services:
            q = q.where(
                self._port_exists(scan_id, d, Port.service_name.in_(f.services))
            )
        if f.cdn == "yes":
            q = q.where(d.c.is_cdn.is_(True))
        elif f.cdn == "no":
            q = q.where(d.c.is_cdn.is_(False))
        if f.alive == "yes":
            q = q.where(d.c.is_alive.is_(True))
        elif f.alive == "no":
            q = q.where(d.c.is_alive.is_(False))
        if f.version in (4, 6):
            q = q.where(d.c.version == f.version)
        if f.sensitive:
            q = q.where(d.c.sensitive.is_(True))
        if f.hosted:
            q = q.where(d.c.host_count > 0)
        if f.open:
            q = q.where(d.c.port_count > 0)
        return q

    @staticmethod
    def _order(q, d, f: IpGroupFilter):
        ip_num = cast(d.c.ip, INET)
        col = {
            "hosts": d.c.host_count,
            "ports": d.c.port_count,
            "assets": d.c.asset_count,
            "asn": d.c.asn,
            "country": d.c.country,
        }.get(f.sort, ip_num)
        primary = col.desc() if f.order == "desc" else col.asc()
        return q.order_by(primary.nulls_last(), ip_num.asc())

    def _scoped(self, scan_id: UUID, f: IpGroupFilter, columns=None):
        d = self._derived(scan_id)
        base = select(d) if columns is None else select(*columns(d))
        return d, self._apply_filter(base, d, f, scan_id)

    @staticmethod
    def _context(scan_id: UUID, d, now: datetime) -> IpQueryContext:
        return IpQueryContext(scan_id=scan_id, now=now, source=d)

    async def search(self, scan_id: UUID, f: IpGroupFilter) -> IpGroupPage:
        now = utc_now()
        d, base = self._scoped(scan_id, f)
        try:
            predicate = compile_ip_query(
                parse_query(f.q, IP_QUERY), self._context(scan_id, d, now)
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
        ports_by_ip, hosts_by_ip = await self._page_details(scan_id, page_ips)
        for r in rows:
            host_set = hosts_by_ip.get(r["ip"], set())
            page.items.append(
                IpGroupRead(
                    ip=r["ip"],
                    version=r["version"],
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

    async def leads(self, scan_id: UUID, f: IpGroupFilter) -> QueryLeads:
        now = utc_now()
        d, base = self._scoped(scan_id, f, columns=lambda d: (d.c.ip,))
        ctx = self._context(scan_id, d, now)
        await self.session.execute(text(STATEMENT_TIMEOUT))
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

    async def groups(self, scan_id: UUID, f: IpGroupFilter, key: str) -> QueryGroups:
        now = utc_now()
        d, base = self._scoped(scan_id, f)
        try:
            predicate = compile_ip_query(
                parse_query(f.q, IP_QUERY), self._context(scan_id, d, now)
            )
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        try:
            return await build_ip_groups(self.session, base, key, scan_id)
        except DBAPIError as exc:
            await self.session.rollback()
            logger.info("address groups failed", error=str(exc.orig))
            return QueryGroups(dimension=key)

    async def facets(self, scan_id: UUID) -> IpFacets:
        d = self._derived(scan_id)
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
                .where(Port.scan_id == scan_id)
                .group_by(Port.number)
                .order_by(ips.desc())
                .limit(_FACET_LIMIT)
            )
        ).all()
        service_rows = (
            await self.session.execute(
                select(Port.service_name, ips)
                .where(Port.scan_id == scan_id, Port.service_name.isnot(None))
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
