from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import (
    Text,
    and_,
    case,
    cast,
    distinct,
    exists,
    false,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.http_asset import HttpAssetService
from app.services.ip_address import IpAddressService
from app.services.port import PortService
from shared.definitions.ports import SENSITIVE_PORTS
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan_correlation import (
    AttentionItem,
    Bucket,
    ClusterStat,
    SubdomainCorrelation,
    SubdomainInsights,
    SurfaceStat,
    Tally,
)
from shared.models.subdomain import (
    Facet,
    Subdomain,
    SubdomainFacets,
    SubdomainFilter,
    SubdomainRead,
    SubdomainRelation,
    SubdomainRow,
    SubdomainSearchResult,
    SubdomainSummary,
    TargetSubdomainRead,
)
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_TARGET_ROLLUP_CAP = 20000
_FACET_LIMIT = 40
_RELATION_CAP = 300
_HTTP_OK = 200
_HTTP_REDIRECT = 300
_HTTP_CLIENT = 400
_HTTP_SERVER = 500
_HTTP_MAX = 600
_AUTH_STATUS = (401, 403)
_STATUS_BUCKETS = {
    "2xx": (_HTTP_OK, _HTTP_REDIRECT),
    "3xx": (_HTTP_REDIRECT, _HTTP_CLIENT),
    "4xx": (_HTTP_CLIENT, _HTTP_SERVER),
    "5xx": (_HTTP_SERVER, _HTTP_MAX),
}
_SENSITIVE_PORTS = SENSITIVE_PORTS
_STATUS_LABELS = {
    "2xx": "2xx OK",
    "3xx": "3xx Redirect",
    "4xx": "4xx Client",
    "5xx": "5xx Server",
    "none": "No HTTP",
}
_CERT_LABELS = {
    "expired": "Expired",
    "expiring": "Expiring <30d",
    "self-signed": "Self-signed",
    "valid": "Valid",
}
_AUTH_RE = "login|sign ?in|log ?in|admin|dashboard|portal|console|authenticat"
_REFRAME = {
    "live": ("Live", "success"),
    "redirect": ("Redirect", "info"),
    "auth": ("Auth required", "warning"),
    "error": ("Broken", "destructive"),
    "none": ("No HTTP", "muted"),
}
_REFRAME_ORDER = ["live", "redirect", "auth", "error", "none"]
_EXPIRY = {
    "expired": ("Expired", "destructive"),
    "d7": ("< 7 days", "destructive"),
    "d30": ("< 30 days", "warning"),
    "d90": ("< 90 days", "info"),
    "ok": ("> 90 days", "success"),
}
_EXPIRY_ORDER = ["expired", "d7", "d30", "d90", "ok"]
_CLUSTER_REASON = {
    "cert": "share a TLS certificate",
    "favicon": "share a favicon hash",
    "ip": "resolve to one IP",
    "cname": "share a CNAME target",
}
_CLUSTER_MIN = 3
_CLUSTER_LIMIT = 8


def _json_facet_sql(column: str, search: bool = False):
    where = " AND v ILIKE :q" if search else ""
    return text(
        f"SELECT v AS value, count(*) AS c "  # noqa: S608
        f"FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.{column} AS jsonb)) v "
        f"WHERE s.project_id = :pid AND s.scan_id = :sid{where} "
        f"GROUP BY v ORDER BY c DESC, v ASC LIMIT :lim"
    )


def _json_distinct_sql(column: str):
    return text(
        f"SELECT count(DISTINCT v) "  # noqa: S608
        f"FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.{column} AS jsonb)) v "
        f"WHERE s.project_id = :pid AND s.scan_id = :sid"
    )


_FACET_SQL = {"tech": _json_facet_sql("tech"), "sources": _json_facet_sql("sources")}
_FACET_SEARCH_SQL = {"tech": _json_facet_sql("tech", search=True)}
_DISTINCT_SQL = {"tech": _json_distinct_sql("tech")}
_TECH_LIMIT = 200
_TOP_TECH = 12


class SubdomainService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_read(self, sub: Subdomain) -> SubdomainRead:
        return SubdomainRead(
            id=sub.id,
            scan_id=sub.scan_id,
            target_id=sub.target_id,
            name=sub.name,
            sources=list(sub.sources or []),
            resolved_ips=list(sub.resolved_ips or []),
            cname=sub.cname,
            is_active=sub.is_active,
            is_wildcard=sub.is_wildcard,
            is_excluded=sub.is_excluded,
            is_important=sub.is_important,
            http_url=sub.http_url,
            final_url=sub.final_url,
            http_status=sub.http_status,
            page_title=sub.page_title,
            content_type=sub.content_type,
            content_length=sub.content_length,
            response_time=sub.response_time,
            webserver=sub.webserver,
            tech=list(sub.tech or []),
            is_cdn=sub.is_cdn,
            cdn_name=sub.cdn_name,
            waf=sub.waf,
            asn=sub.asn,
            asn_org=sub.asn_org,
            favicon_hash=sub.favicon_hash,
            tls_not_after=sub.tls_not_after,
            tls_expired=sub.tls_expired,
            tls_self_signed=sub.tls_self_signed,
            screenshot_path=sub.screenshot_path,
            discovered_at=sub.discovered_at,
        )

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        active_only: bool,
        search: str | None,
    ):
        query = select(Subdomain).where(Subdomain.project_id == project_id)
        if scan_id is not None:
            query = query.where(Subdomain.scan_id == scan_id)
        if target_id is not None:
            query = query.where(Subdomain.target_id == target_id)
        if active_only:
            query = query.where(Subdomain.is_active == True)  # noqa: E712
        if search:
            query = query.where(Subdomain.name.ilike(f"%{search}%"))
        return query

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
        active_only: bool = False,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SubdomainRead]:
        query = self._base_query(project_id, scan_id, target_id, active_only, search)
        query = query.order_by(Subdomain.name).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_read(s) for s in result.scalars().all()]

    async def summary(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> SubdomainSummary:
        query = self._base_query(project_id, scan_id, target_id, False, None)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        source_counts: Counter = Counter()
        active = 0
        for row in rows:
            if row.is_active:
                active += 1
            for src in row.sources or []:
                source_counts[src] += 1
        return SubdomainSummary(
            total=len(rows), active=active, sources=dict(source_counts)
        )

    # ── server-side faceted search (Web Assets table) ──────────────────

    @staticmethod
    def _status_pred(s: str):
        if s == "none":
            return Subdomain.http_status.is_(None)
        bucket = _STATUS_BUCKETS.get(s)
        if bucket is None:
            return false()
        return and_(
            Subdomain.http_status >= bucket[0], Subdomain.http_status < bucket[1]
        )

    @staticmethod
    def _cert_pred(c: str, now: datetime):
        if c == "self-signed":
            return Subdomain.tls_self_signed.is_(True)
        if c == "expired":
            return or_(
                Subdomain.tls_expired.is_(True),
                and_(
                    Subdomain.tls_not_after.isnot(None), Subdomain.tls_not_after < now
                ),
            )
        if c == "expiring":
            return and_(
                Subdomain.tls_not_after.isnot(None),
                Subdomain.tls_expired.isnot(True),
                Subdomain.tls_not_after >= now,
                Subdomain.tls_not_after < now + timedelta(days=30),
            )
        if c == "valid":
            return and_(
                Subdomain.tls_not_after.isnot(None),
                Subdomain.tls_not_after >= now + timedelta(days=30),
                Subdomain.tls_self_signed.isnot(True),
            )
        return false()

    @staticmethod
    def _port_exists(cond):
        return exists().where(
            and_(
                Port.scan_id == Subdomain.scan_id,
                cond,
                func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), Port.ip),
            )
        )

    def _apply_filter(self, query, f: SubdomainFilter, now: datetime):  # noqa: PLR0912, PLR0915
        if f.text:
            for word in f.text.split():
                like = f"%{word}%"
                query = query.where(
                    or_(
                        Subdomain.name.ilike(like),
                        Subdomain.page_title.ilike(like),
                        Subdomain.webserver.ilike(like),
                        cast(Subdomain.resolved_ips, Text).ilike(like),
                        cast(Subdomain.tech, Text).ilike(like),
                    )
                )
        if f.statuses:
            query = query.where(or_(*[self._status_pred(s) for s in f.statuses]))
        if f.tech:
            query = query.where(
                func.jsonb_exists_any(cast(Subdomain.tech, JSONB), pg_array(f.tech))
            )
        if f.sources:
            query = query.where(
                func.jsonb_exists_any(
                    cast(Subdomain.sources, JSONB), pg_array(f.sources)
                )
            )
        if f.cert:
            query = query.where(or_(*[self._cert_pred(c, now) for c in f.cert]))
        if f.services:
            query = query.where(self._port_exists(Port.service_name.in_(f.services)))
        if f.ports:
            query = query.where(self._port_exists(Port.number.in_(f.ports)))
        if f.sensitive:
            query = query.where(self._port_exists(Port.number.in_(_SENSITIVE_PORTS)))
        if f.cdn == "yes":
            query = query.where(Subdomain.is_cdn.is_(True))
        elif f.cdn == "no":
            query = query.where(Subdomain.is_cdn.is_(False))
        if f.waf == "present":
            query = query.where(Subdomain.waf.isnot(None))
        elif f.waf == "none":
            query = query.where(Subdomain.waf.is_(None))
        if f.live:
            query = query.where(
                and_(
                    Subdomain.http_status >= _HTTP_OK,
                    Subdomain.http_status < _HTTP_CLIENT,
                )
            )
        if f.screenshot:
            query = query.where(Subdomain.screenshot_path.isnot(None))
        if f.important:
            query = query.where(Subdomain.is_important.is_(True))
        if f.wildcard:
            query = query.where(Subdomain.is_wildcard.is_(True))
        if f.new:
            query = query.where(~self._seen_earlier())
        if f.resolved:
            query = query.where(
                func.jsonb_array_length(cast(Subdomain.resolved_ips, JSONB)) > 0
            )
        if f.auth:
            query = query.where(
                or_(
                    Subdomain.http_status.in_(_AUTH_STATUS),
                    Subdomain.page_title.op("~*")(_AUTH_RE),
                )
            )
        if f.ip:
            query = query.where(cast(Subdomain.resolved_ips, Text).ilike(f"%{f.ip}%"))
        if f.cname:
            query = query.where(Subdomain.cname.ilike(f"%{f.cname}%"))
        if f.favicon:
            query = query.where(Subdomain.favicon_hash == f.favicon)
        if f.title:
            query = query.where(Subdomain.page_title.ilike(f"%{f.title}%"))
        if f.title_exact:
            query = query.where(Subdomain.page_title == f.title_exact)
        if f.issues:
            query = query.where(
                or_(
                    self._cert_pred("expired", now),
                    self._cert_pred("expiring", now),
                    Subdomain.tls_self_signed.is_(True),
                    Subdomain.http_status >= _HTTP_SERVER,
                    and_(
                        Subdomain.http_status >= _HTTP_OK,
                        Subdomain.http_status < _HTTP_CLIENT,
                        Subdomain.waf.is_(None),
                        Subdomain.is_cdn.is_(False),
                    ),
                    self._port_exists(Port.number.in_(_SENSITIVE_PORTS)),
                )
            )
        return query

    @staticmethod
    def _seen_earlier():
        earlier = aliased(Subdomain)
        return exists(
            select(1).where(
                earlier.target_id == Subdomain.target_id,
                earlier.name == Subdomain.name,
                earlier.scan_id != Subdomain.scan_id,
                earlier.discovered_at < Subdomain.discovered_at,
            )
        )

    @staticmethod
    def _order(query, f: SubdomainFilter):
        col = {
            "status": Subdomain.http_status,
            "size": Subdomain.content_length,
            "time": Subdomain.response_time,
            "title": Subdomain.page_title,
            "cert": Subdomain.tls_not_after,
            "discovered": Subdomain.discovered_at,
            "ip": cast(Subdomain.resolved_ips, JSONB).op("->>")(0),
        }.get(f.sort, Subdomain.name)
        primary = col.desc() if f.order == "desc" else col.asc()
        return query.order_by(primary.nulls_last(), Subdomain.name.asc())

    async def search(
        self, project_id: UUID, scan_id: UUID, f: SubdomainFilter
    ) -> SubdomainSearchResult:
        now = utc_now()
        base = select(Subdomain).where(
            Subdomain.project_id == project_id, Subdomain.scan_id == scan_id
        )
        base = self._apply_filter(base, f, now)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        page = self._order(base, f).limit(f.limit).offset(f.offset)
        result = await self.session.execute(page)
        rows = result.scalars().all()

        all_ips = {ip for s in rows for ip in (s.resolved_ips or [])}
        ports_by_ip: dict[str, set[int]] = {}
        if all_ips:
            port_rows = await self.session.execute(
                select(Port.ip, Port.number).where(
                    Port.scan_id == scan_id, Port.ip.in_(all_ips)
                )
            )
            for ip, number in port_rows.all():
                ports_by_ip.setdefault(ip, set()).add(number)

        title_counts = await self._shared_counts(
            scan_id, Subdomain.page_title, {s.page_title for s in rows if s.page_title}
        )
        favicon_counts = await self._shared_counts(
            scan_id,
            Subdomain.favicon_hash,
            {s.favicon_hash for s in rows if s.favicon_hash},
        )
        items = []
        for s in rows:
            nums: set[int] = set()
            for ip in s.resolved_ips or []:
                nums |= ports_by_ip.get(ip, set())
            items.append(
                SubdomainRow(
                    **self._to_read(s).model_dump(),
                    ports=sorted(nums),
                    title_count=title_counts.get(s.page_title, 0),
                    favicon_count=favicon_counts.get(s.favicon_hash, 0),
                )
            )
        return SubdomainSearchResult(items=items, total=int(total or 0))

    async def _shared_counts(self, scan_id: UUID, col, values: set) -> dict:
        if not values:
            return {}
        rows = await self.session.execute(
            select(col, func.count())
            .where(Subdomain.scan_id == scan_id, col.in_(values))
            .group_by(col)
        )
        return {value: int(n) for value, n in rows.all()}

    async def facets(self, project_id: UUID, scan_id: UUID) -> SubdomainFacets:
        now = utc_now()
        scope = (Subdomain.project_id == project_id, Subdomain.scan_id == scan_id)

        # driven from _STATUS_BUCKETS so the facet matches `_status_pred` exactly
        status_key = case(
            (Subdomain.http_status.is_(None), "none"),
            *[
                (
                    and_(Subdomain.http_status >= lo, Subdomain.http_status < hi),
                    bucket,
                )
                for bucket, (lo, hi) in _STATUS_BUCKETS.items()
            ],
            else_=None,
        )
        status_rows = await self.session.execute(
            select(status_key.label("k"), func.count())
            .where(*scope)
            .group_by(status_key)
        )
        order = ["2xx", "3xx", "4xx", "5xx", "none"]
        status_map = {k: c for k, c in status_rows.all() if k is not None}
        status = [
            Facet(value=k, label=_STATUS_LABELS[k], count=status_map[k])
            for k in order
            if k in status_map
        ]

        # per-state counts (overlapping) so each facet matches its `cert:<state>` filter
        cert_counts = (
            await self.session.execute(
                select(
                    func.count()
                    .filter(self._cert_pred("expired", now))
                    .label("expired"),
                    func.count()
                    .filter(self._cert_pred("expiring", now))
                    .label("expiring"),
                    func.count()
                    .filter(self._cert_pred("self-signed", now))
                    .label("self_signed"),
                    func.count().filter(self._cert_pred("valid", now)).label("valid"),
                )
                .select_from(Subdomain)
                .where(*scope)
            )
        ).one()
        cert = [
            Facet(value=value, label=_CERT_LABELS[value], count=count)
            for value, count in [
                ("expired", cert_counts.expired),
                ("expiring", cert_counts.expiring),
                ("self-signed", cert_counts.self_signed),
                ("valid", cert_counts.valid),
            ]
            if count > 0
        ]

        tech = await self._json_facet("tech", project_id, scan_id)
        source = await self._json_facet("sources", project_id, scan_id)

        service_rows = await self.session.execute(
            select(Port.service_name, func.count())
            .where(
                Port.project_id == project_id,
                Port.scan_id == scan_id,
                Port.service_name.isnot(None),
            )
            .group_by(Port.service_name)
            .order_by(func.count().desc())
            .limit(_FACET_LIMIT)
        )
        service = [
            Facet(value=name, label=name, count=count)
            for name, count in service_rows.all()
        ]

        return SubdomainFacets(
            status=status, tech=tech, service=service, source=source, cert=cert
        )

    async def _json_facet(
        self,
        column: str,
        project_id: UUID,
        scan_id: UUID,
        *,
        limit: int = _FACET_LIMIT,
        search: str | None = None,
    ) -> list[Facet]:
        if search:
            stmt = _FACET_SEARCH_SQL[column].bindparams(
                pid=project_id, sid=scan_id, lim=limit, q=f"%{search}%"
            )
        else:
            stmt = _FACET_SQL[column].bindparams(pid=project_id, sid=scan_id, lim=limit)
        rows = await self.session.execute(stmt)
        return [Facet(value=v, label=v, count=c) for v, c in rows.all()]

    async def tech(
        self, project_id: UUID, scan_id: UUID, search: str | None, limit: int
    ) -> list[Facet]:
        return await self._json_facet(
            "tech", project_id, scan_id, limit=min(limit, _TECH_LIMIT), search=search
        )

    async def related(
        self, project_id: UUID, scan_id: UUID, name: str
    ) -> list[SubdomainRelation]:
        target = await self.session.scalar(
            select(Subdomain).where(
                Subdomain.project_id == project_id,
                Subdomain.scan_id == scan_id,
                Subdomain.name == name,
            )
        )
        if target is None:
            return []
        out: list[SubdomainRelation] = []
        others = select(Subdomain.name).where(
            Subdomain.project_id == project_id,
            Subdomain.scan_id == scan_id,
            Subdomain.name != name,
        )

        async def hosts(stmt) -> list[str]:
            res = await self.session.execute(stmt.limit(_RELATION_CAP))
            return list(dict.fromkeys(res.scalars().all()))

        if target.resolved_ips:
            h = await hosts(
                others.where(
                    func.jsonb_exists_any(
                        cast(Subdomain.resolved_ips, JSONB),
                        pg_array(target.resolved_ips),
                    )
                )
            )
            if h:
                out.append(
                    SubdomainRelation(
                        kind="ip",
                        reason=f"Resolve to a shared IP ({target.resolved_ips[0]})",
                        value=target.resolved_ips[0],
                        hosts=h,
                    )
                )
        if target.favicon_hash:
            h = await hosts(others.where(Subdomain.favicon_hash == target.favicon_hash))
            if h:
                out.append(
                    SubdomainRelation(
                        kind="favicon",
                        reason="Same favicon hash",
                        value=target.favicon_hash,
                        hosts=h,
                    )
                )
        if target.cname:
            h = await hosts(others.where(Subdomain.cname == target.cname))
            if h:
                out.append(
                    SubdomainRelation(
                        kind="cname",
                        reason=f"Share CNAME {target.cname}",
                        value=target.cname,
                        hosts=h,
                    )
                )
        if target.asn:
            h = await hosts(others.where(Subdomain.asn == target.asn))
            if h:
                out.append(
                    SubdomainRelation(
                        kind="asn",
                        reason=f"Same network AS{target.asn}"
                        + (f" ({target.asn_org})" if target.asn_org else ""),
                        value=str(target.asn),
                        hosts=h,
                    )
                )
        fp = await self.session.scalar(
            select(HttpAsset.tls_fingerprint)
            .where(
                HttpAsset.scan_id == scan_id,
                HttpAsset.host == name,
                HttpAsset.tls_fingerprint.isnot(None),
            )
            .limit(1)
        )
        if fp:
            res = await self.session.execute(
                select(HttpAsset.host)
                .where(
                    HttpAsset.scan_id == scan_id,
                    HttpAsset.tls_fingerprint == fp,
                    HttpAsset.host != name,
                )
                .distinct()
                .limit(_RELATION_CAP)
            )
            h = list(dict.fromkeys(res.scalars().all()))
            if h:
                out.append(
                    SubdomainRelation(
                        kind="cert",
                        reason="Same TLS certificate",
                        value=fp,
                        hosts=h,
                    )
                )
        return out

    # ── overview insights (server-side aggregation) ────────────────────

    async def _cluster(self, col, kind: str, project_id, scan_id) -> list[ClusterStat]:
        rows = await self.session.execute(
            select(col, func.count().label("c"))
            .where(
                Subdomain.project_id == project_id,
                Subdomain.scan_id == scan_id,
                col.isnot(None),
            )
            .group_by(col)
            .having(func.count() >= _CLUSTER_MIN)
            .order_by(func.count().desc())
            .limit(_CLUSTER_LIMIT)
        )
        return [
            ClusterStat(kind=kind, reason=_CLUSTER_REASON[kind], value=str(v), count=c)
            for v, c in rows.all()
        ]

    async def insights(self, project_id: UUID, scan_id: UUID) -> SubdomainInsights:
        now = utc_now()
        scope = (Subdomain.project_id == project_id, Subdomain.scan_id == scan_id)
        live = and_(
            Subdomain.http_status >= _HTTP_OK, Subdomain.http_status < _HTTP_CLIENT
        )

        counts = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count().filter(live).label("live"),
                    func.count().filter(Subdomain.http_status.isnot(None)).label("web"),
                    func.count()
                    .filter(
                        func.jsonb_array_length(cast(Subdomain.resolved_ips, JSONB)) > 0
                    )
                    .label("resolved"),
                    func.count()
                    .filter(
                        and_(
                            Subdomain.cname.isnot(None),
                            func.jsonb_array_length(cast(Subdomain.resolved_ips, JSONB))
                            == 0,
                        )
                    )
                    .label("cname_only"),
                    func.count()
                    .filter(Subdomain.screenshot_path.isnot(None))
                    .label("shots"),
                    func.count().filter(Subdomain.is_cdn.is_(True)).label("cdn"),
                    func.count().filter(Subdomain.waf.isnot(None)).label("waf"),
                    func.count()
                    .filter(Subdomain.http_status >= _HTTP_SERVER)
                    .label("server_err"),
                    func.count()
                    .filter(Subdomain.tls_self_signed.is_(True))
                    .label("self_signed"),
                    func.count()
                    .filter(self._cert_pred("expired", now))
                    .label("expired"),
                    func.count()
                    .filter(self._cert_pred("expiring", now))
                    .label("expiring"),
                    func.count()
                    .filter(
                        and_(live, Subdomain.waf.is_(None), Subdomain.is_cdn.is_(False))
                    )
                    .label("nowaf"),
                    func.count()
                    .filter(
                        or_(
                            Subdomain.http_status.in_(_AUTH_STATUS),
                            Subdomain.page_title.op("~*")(_AUTH_RE),
                        )
                    )
                    .label("auth"),
                )
                .select_from(Subdomain)
                .where(*scope)
            )
        ).one()

        sensitive = await self.session.scalar(
            select(func.count())
            .select_from(Subdomain)
            .where(*scope, self._port_exists(Port.number.in_(_SENSITIVE_PORTS)))
        )
        ip_total = await self.session.scalar(
            select(func.count())
            .select_from(IpAddress)
            .where(IpAddress.project_id == project_id, IpAddress.scan_id == scan_id)
        )
        if not ip_total:
            ip_total = await self.session.scalar(
                text(
                    "SELECT count(DISTINCT ip) FROM subdomains s, "
                    "LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip "
                    "WHERE s.project_id = :pid AND s.scan_id = :sid"
                ).bindparams(pid=project_id, sid=scan_id)
            )
        asn_total = await self.session.scalar(
            select(func.count(distinct(IpAddress.asn))).where(
                IpAddress.project_id == project_id,
                IpAddress.scan_id == scan_id,
                IpAddress.asn.isnot(None),
            )
        )
        port_total = await self.session.scalar(
            select(func.count())
            .select_from(Port)
            .where(Port.project_id == project_id, Port.scan_id == scan_id)
        )

        surface = [
            SurfaceStat(key="subdomains", label="Subdomains", value=counts.total),
            SurfaceStat(
                key="resolved",
                label="Resolved",
                value=counts.resolved,
                filter="is:resolved",
            ),
            SurfaceStat(key="live", label="Live", value=counts.live, filter="is:live"),
            SurfaceStat(key="web", label="With web", value=counts.web, filter="is:web"),
            SurfaceStat(
                key="screenshot",
                label="Screenshots",
                value=counts.shots,
                filter="is:screenshot",
            ),
            SurfaceStat(
                key="cdn", label="Behind CDN", value=counts.cdn, filter="cdn:yes"
            ),
            SurfaceStat(
                key="waf", label="Behind WAF", value=counts.waf, filter="waf:any"
            ),
            SurfaceStat(key="ips", label="Unique IPs", value=int(ip_total or 0)),
            SurfaceStat(key="asns", label="Networks", value=int(asn_total or 0)),
            SurfaceStat(key="ports", label="Open ports", value=int(port_total or 0)),
        ]

        raw_attention = [
            ("expired", "Expired certs", counts.expired, "cert:expired", "destructive"),
            (
                "expiring",
                "Certs expiring <30d",
                counts.expiring,
                "cert:expiring",
                "warning",
            ),
            (
                "selfsigned",
                "Self-signed certs",
                counts.self_signed,
                "cert:self-signed",
                "warning",
            ),
            (
                "nowaf",
                "Live hosts, no WAF",
                counts.nowaf,
                "is:live waf:none",
                "warning",
            ),
            (
                "server",
                "Server errors (5xx)",
                counts.server_err,
                "status:5xx",
                "destructive",
            ),
            ("auth", "Auth / login panels", counts.auth, "is:auth", "warning"),
            (
                "sensitive",
                "Exposed sensitive services",
                int(sensitive or 0),
                "sensitive:true",
                "destructive",
            ),
        ]
        attention = [
            AttentionItem(key=k, label=lbl, count=n, filter=flt, tone=tone)
            for k, lbl, n, flt, tone in raw_attention
            if n > 0
        ]

        sources = [
            Tally(name=f.value, count=f.count)
            for f in (await self._json_facet("sources", project_id, scan_id))[:8]
        ]
        unresolved = counts.total - counts.resolved - counts.cname_only
        resolution = [
            Bucket(key=k, label=lbl, count=n, klass=klass)
            for k, lbl, n, klass in (
                ("resolved", "Resolves to an IP", counts.resolved, "success"),
                ("cname", "CNAME only", counts.cname_only, "info"),
                ("unresolved", "No DNS answer", unresolved, "muted"),
            )
            if n > 0
        ]

        reframe_key = case(
            (Subdomain.http_status.is_(None), "none"),
            (Subdomain.http_status < _HTTP_REDIRECT, "live"),
            (Subdomain.http_status < _HTTP_CLIENT, "redirect"),
            (Subdomain.http_status.in_(_AUTH_STATUS), "auth"),
            else_="error",
        )
        reframe_rows = dict(
            (
                await self.session.execute(
                    select(reframe_key.label("k"), func.count())
                    .where(*scope)
                    .group_by(reframe_key)
                )
            ).all()
        )
        status_reframe = [
            Bucket(
                key=k, label=_REFRAME[k][0], count=reframe_rows[k], klass=_REFRAME[k][1]
            )
            for k in _REFRAME_ORDER
            if reframe_rows.get(k)
        ]

        cb_key = case(
            (self._cert_pred("expired", now), "expired"),
            (Subdomain.tls_not_after < now + timedelta(days=7), "d7"),
            (Subdomain.tls_not_after < now + timedelta(days=30), "d30"),
            (Subdomain.tls_not_after < now + timedelta(days=90), "d90"),
            (Subdomain.tls_not_after.isnot(None), "ok"),
            else_=None,
        )
        cb_rows = {
            k: c
            for k, c in (
                await self.session.execute(
                    select(cb_key.label("k"), func.count())
                    .where(*scope)
                    .group_by(cb_key)
                )
            ).all()
            if k is not None
        }
        cert_buckets = [
            Bucket(key=k, label=_EXPIRY[k][0], count=cb_rows[k], klass=_EXPIRY[k][1])
            for k in _EXPIRY_ORDER
            if cb_rows.get(k)
        ]

        top_tech = [
            Tally(name=f.value, count=f.count)
            for f in await self._json_facet(
                "tech", project_id, scan_id, limit=_TOP_TECH
            )
        ]
        tech_total = int(
            await self.session.scalar(
                _DISTINCT_SQL["tech"].bindparams(pid=project_id, sid=scan_id)
            )
            or 0
        )
        asn_rows = await self.session.execute(
            select(IpAddress.asn_org, func.count())
            .where(
                IpAddress.project_id == project_id,
                IpAddress.scan_id == scan_id,
                IpAddress.asn_org.isnot(None),
            )
            .group_by(IpAddress.asn_org)
            .order_by(func.count().desc())
            .limit(8)
        )
        top_asn = [Tally(name=n, count=c) for n, c in asn_rows.all()]
        service_rows = await self.session.execute(
            select(Port.service_name, func.count())
            .where(
                Port.project_id == project_id,
                Port.scan_id == scan_id,
                Port.service_name.isnot(None),
            )
            .group_by(Port.service_name)
            .order_by(func.count().desc())
            .limit(8)
        )
        services = [Tally(name=n, count=c) for n, c in service_rows.all()]

        clusters: list[ClusterStat] = []
        clusters += await self._cluster(
            Subdomain.favicon_hash, "favicon", project_id, scan_id
        )
        clusters += await self._cluster(Subdomain.cname, "cname", project_id, scan_id)
        ip_cluster_rows = await self.session.execute(
            text(
                "SELECT ip AS value, count(*) AS c "
                "FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip "
                "WHERE s.project_id = :pid AND s.scan_id = :sid "
                "GROUP BY ip HAVING count(*) >= :mn ORDER BY c DESC LIMIT :lim"
            ).bindparams(
                pid=project_id, sid=scan_id, mn=_CLUSTER_MIN, lim=_CLUSTER_LIMIT
            )
        )
        clusters += [
            ClusterStat(kind="ip", reason=_CLUSTER_REASON["ip"], value=v, count=c)
            for v, c in ip_cluster_rows.all()
        ]
        cert_cluster_rows = await self.session.execute(
            select(HttpAsset.tls_fingerprint, func.count(distinct(HttpAsset.host)))
            .where(
                HttpAsset.project_id == project_id,
                HttpAsset.scan_id == scan_id,
                HttpAsset.tls_fingerprint.isnot(None),
            )
            .group_by(HttpAsset.tls_fingerprint)
            .having(func.count(distinct(HttpAsset.host)) >= _CLUSTER_MIN)
            .order_by(func.count(distinct(HttpAsset.host)).desc())
            .limit(_CLUSTER_LIMIT)
        )
        clusters += [
            ClusterStat(kind="cert", reason=_CLUSTER_REASON["cert"], value=v, count=c)
            for v, c in cert_cluster_rows.all()
        ]
        clusters.sort(key=lambda c: c.count, reverse=True)

        return SubdomainInsights(
            surface=surface,
            attention=attention,
            sources=sources,
            resolution=resolution,
            status_reframe=status_reframe,
            cert_buckets=cert_buckets,
            top_tech=top_tech,
            tech_total=tech_total,
            top_asn=top_asn,
            services=services,
            clusters=clusters[:_CLUSTER_LIMIT],
        )

    @staticmethod
    def _asset_rank(a: HttpAsset) -> tuple:
        alive = a.status_code is not None and _HTTP_OK <= a.status_code < _HTTP_CLIENT
        return (a.scheme == "https", alive, a.port in (443, 80), -(a.port or 0))

    async def correlation(
        self, project_id: UUID, scan_id: UUID, name: str
    ) -> SubdomainCorrelation:
        sub = await self.session.scalar(
            select(Subdomain).where(
                Subdomain.project_id == project_id,
                Subdomain.scan_id == scan_id,
                Subdomain.name == name,
            )
        )
        ips = list(sub.resolved_ips or []) if sub else []
        ha = HttpAssetService(self.session)
        asset_rows = (
            (
                await self.session.execute(
                    select(HttpAsset)
                    .where(HttpAsset.scan_id == scan_id, HttpAsset.host == name)
                    .order_by(HttpAsset.port)
                )
            )
            .scalars()
            .all()
        )
        services = [ha._to_read(a) for a in asset_rows]
        primary = max(asset_rows, key=self._asset_rank) if asset_rows else None

        ports: list = []
        ip_metas: list = []
        if ips:
            port_rows = (
                (
                    await self.session.execute(
                        select(Port)
                        .where(Port.scan_id == scan_id, Port.ip.in_(ips))
                        .order_by(Port.number)
                    )
                )
                .scalars()
                .all()
            )
            ps = PortService(self.session)
            ports = [ps._to_read(p) for p in port_rows]
            ip_rows = (
                (
                    await self.session.execute(
                        select(IpAddress).where(
                            IpAddress.scan_id == scan_id, IpAddress.ip.in_(ips)
                        )
                    )
                )
                .scalars()
                .all()
            )
            isvc = IpAddressService(self.session)
            ip_metas = [isvc._to_read(i) for i in ip_rows]

        related = await self.related(project_id, scan_id, name)
        return SubdomainCorrelation(
            primary_asset=ha._to_read(primary) if primary else None,
            services=services,
            ports=ports,
            ip_metas=ip_metas,
            related=related,
        )

    async def _fetch_target_rows(
        self, project_id: UUID, target_id: UUID
    ) -> list[Subdomain]:
        query = (
            select(Subdomain)
            .where(Subdomain.project_id == project_id, Subdomain.target_id == target_id)
            .order_by(Subdomain.discovered_at.desc(), Subdomain.scan_id.desc())
            .limit(_TARGET_ROLLUP_CAP + 1)
        )
        result = await self.session.execute(query)
        rows = list(result.scalars().all())
        if len(rows) > _TARGET_ROLLUP_CAP:
            logger.warning(
                "target %s rollup capped at %d rows (newest kept)",
                target_id,
                _TARGET_ROLLUP_CAP,
            )
            rows = rows[:_TARGET_ROLLUP_CAP]
        # fetched newest-first to keep the latest scan under the cap; _aggregate
        # needs ascending so the newest row wins on overwrite (deterministic tie-break)
        rows.sort(key=lambda r: (r.discovered_at, str(r.scan_id)))
        return rows

    @staticmethod
    def _aggregate(rows: list[Subdomain]) -> dict[str, TargetSubdomainRead]:
        agg: dict[str, TargetSubdomainRead] = {}
        scan_ids: dict[str, set] = {}
        for (
            row
        ) in rows:  # ordered by discovered_at asc, so latest row wins on overwrite
            existing = agg.get(row.name)
            if existing is None:
                scan_ids[row.name] = {row.scan_id}
                agg[row.name] = TargetSubdomainRead(
                    name=row.name,
                    sources=list(row.sources or []),
                    resolved_ips=list(row.resolved_ips or []),
                    cname=row.cname,
                    is_active=row.is_active,
                    is_wildcard=row.is_wildcard,
                    is_excluded=row.is_excluded,
                    scan_count=1,
                    last_scan_id=row.scan_id,
                    first_seen=row.discovered_at,
                    last_seen=row.discovered_at,
                )
                continue
            scan_ids[row.name].add(row.scan_id)
            existing.sources = sorted(set(existing.sources) | set(row.sources or []))
            existing.resolved_ips = list(row.resolved_ips or [])
            existing.cname = row.cname
            existing.is_active = row.is_active
            existing.is_wildcard = row.is_wildcard
            existing.is_excluded = row.is_excluded
            existing.last_scan_id = row.scan_id
            existing.last_seen = row.discovered_at
            existing.scan_count = len(scan_ids[row.name])
        return agg

    async def list_for_target(
        self,
        project_id: UUID,
        target_id: UUID,
        active_only: bool = False,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TargetSubdomainRead]:
        rows = await self._fetch_target_rows(project_id, target_id)
        items = list(self._aggregate(rows).values())
        if active_only:
            items = [i for i in items if i.is_active]
        if search:
            needle = search.lower()
            items = [i for i in items if needle in i.name.lower()]
        items.sort(key=lambda i: i.name)
        return items[offset : offset + limit]

    async def summary_for_target(
        self, project_id: UUID, target_id: UUID
    ) -> SubdomainSummary:
        rows = await self._fetch_target_rows(project_id, target_id)
        agg = self._aggregate(rows)
        source_counts: Counter = Counter()
        active = 0
        for item in agg.values():
            if item.is_active:
                active += 1
            for src in item.sources:
                source_counts[src] += 1
        return SubdomainSummary(
            total=len(agg), active=active, sources=dict(source_counts)
        )

    async def count(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> int:
        query = select(func.count()).select_from(
            self._base_query(project_id, scan_id, target_id, False, None).subquery()
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())
