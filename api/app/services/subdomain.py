from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import (
    and_,
    case,
    cast,
    distinct,
    func,
    not_,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.util import ClauseAdapter

from app.services.cross_links import CrossLinkService
from app.services.http_asset import HttpAssetService
from app.services.ip_address import IpAddressService
from app.services.port import PortService
from app.services.target_names import target_names
from shared.definitions import domain_posture as posture_defs
from shared.definitions import hygiene as hygiene_defs
from shared.definitions.asset_query import (
    ALL_TAB,
    COUNT_CAP,
    HOST_QUERY,
    MAX_GROUPS,
    RENDER_SAMPLE_HOSTS,
    STATUS_CLASSES,
)
from shared.definitions.correlation import (
    CORRELATION_KIND_LABELS,
    CORRELATION_KIND_ORDER,
    CORRELATION_RELATION_PHRASE,
    SCREENSHOT_DISTANCE,
)
from shared.definitions.interest import TONE_INFO, TONE_WARNING
from shared.definitions.ports import SENSITIVE_PORTS, port_interest
from shared.definitions.vulnerabilities import SEVERITY_ORDER
from shared.logging import get_logger
from shared.models.asset_query import (
    QueryCounts,
    QueryGroups,
    QueryLeads,
)
from shared.models.endpoint import Endpoint
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
    HygieneCheckCount,
    HygieneSummary,
    RenderGroup,
    RenderGroups,
    Subdomain,
    SubdomainFacets,
    SubdomainFilter,
    SubdomainRead,
    SubdomainRelation,
    SubdomainRow,
    SubdomainSearchResult,
)
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryContext,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    build_groups,
    build_leads,
    collect_evidence,
    compile_query,
    count_named,
    count_queries,
    lead_cache,
    parse_query,
    query_error_for,
    syntax_error,
    vuln_suppressed,
)
from shared.services.asset_query import predicates as preds
from shared.services.asset_query.renders import cluster, is_identity
from shared.services.correlation import CorrelationFinder, values_carried
from shared.services.surface_query import web_assets as surface_hosts
from shared.utils.datetime import utc_now
from shared.utils.imagehash import distance, hex_digest
from shared.utils.infra import generic_page

logger = get_logger(__name__)

_NO_FINDINGS: tuple[int, str | None, bool, dict[str, int]] = (0, None, False, {})
_NO_SHARE: tuple[int, int] = (0, 1)

_FACET_LIMIT = 40
_RELATION_CAP = 300
_CERT_LABELS = {
    "expired": "Expired",
    "expiring": "Expiring <30d",
    "self-signed": "Self-signed",
    "valid": "Valid",
}
_REFRAME = {
    "live": ("2xx responses", "success"),
    "redirect": ("3xx redirects", "info"),
    "auth": ("Authentication required", "warning"),
    "error": ("4xx and 5xx errors", "destructive"),
    "none": ("No HTTP response", "muted"),
}
_REFRAME_ORDER = ["live", "redirect", "auth", "error", "none"]
_EXPIRY = {
    "expired": ("Expired", "destructive"),
    "week": ("Expires within 7 days", "destructive"),
    "month": ("Expires within 30 days", "warning"),
    "quarter": ("Expires within 90 days", "info"),
    "later": ("Valid beyond 90 days", "success"),
}
_EXPIRY_ORDER = ["expired", "week", "month", "quarter", "later"]
_CLUSTER_REASON = {
    "cert": "Shared TLS certificate",
    "favicon": "Shared favicon hash",
    "ip": "Shared IP address",
    "cname": "Shared CNAME target",
}
_CLUSTER_MIN = 3
_CLUSTER_LIMIT = 8


def _json_facet_sql(column: str, search: bool = False):
    where = " AND v ILIKE :q" if search else ""
    return text(
        f"SELECT v AS value, count(*) AS c "  # noqa: S608
        f"FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.{column} AS jsonb)) v "
        f"WHERE s.project_id = :pid AND s.scan_id = ANY(:sids){where} "
        f"GROUP BY v ORDER BY c DESC, v ASC LIMIT :lim"
    )


def _json_distinct_sql(column: str):
    return text(
        f"SELECT count(DISTINCT v) "  # noqa: S608
        f"FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.{column} AS jsonb)) v "
        f"WHERE s.project_id = :pid AND s.scan_id = ANY(:sids)"
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
            hygiene_issues=list(sub.hygiene_issues or []),
            hygiene_checked=list(sub.hygiene_checked or []),
            posture_issues=list(sub.posture_issues or []),
            posture_checked=list(sub.posture_checked or []),
            ai_services=None if sub.ai_services is None else list(sub.ai_services),
            discovered_at=sub.discovered_at,
        )

    # ── server-side faceted search (Web Assets table) ──────────────────

    _cert_pred = staticmethod(preds.cert_state)

    _apply_filter = staticmethod(surface_hosts.apply_filter)
    _order = staticmethod(surface_hosts.order)
    _scoped = staticmethod(surface_hosts.scoped)

    async def search(
        self, project_id: UUID, scope: ScopeLike, f: SubdomainFilter
    ) -> SubdomainSearchResult:
        now = utc_now()
        scope = QueryScope.of(scope)
        base = self._scoped(project_id, scope, f, now)
        try:
            node = parse_query(f.q)
            predicate = compile_query(node, QueryContext(scope=scope, now=now))
        except QuerySyntaxError as exc:
            return SubdomainSearchResult(error=syntax_error(exc))
        if predicate is not None:
            base = base.where(predicate)

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            counted = await self.session.scalar(
                select(func.count()).select_from(base.limit(COUNT_CAP + 1).subquery())
            )
            page = self._order(base, f).limit(f.limit).offset(f.offset)
            result = await self.session.execute(page)
            rows = list(result.scalars().all())
        except DBAPIError as exc:
            await self.session.rollback()
            rejected = query_error_for(exc)
            if rejected is None:
                raise
            logger.info("asset query rejected by postgres", error=str(exc.orig))
            return SubdomainSearchResult(error=rejected)
        total = int(counted or 0)
        capped = total > COUNT_CAP

        all_ips = {ip for s in rows for ip in (s.resolved_ips or [])}
        ports_by_ip: dict[str, set[int]] = {}
        if all_ips:
            port_rows = await self.session.execute(
                select(Port.ip, Port.number).where(
                    scope.match(Port.scan_id), Port.ip.in_(all_ips)
                )
            )
            for ip, number in port_rows.all():
                ports_by_ip.setdefault(ip, set()).add(number)

        title_counts = await self._shared_counts(
            scope,
            Subdomain.page_title,
            {s.page_title for s in rows if s.page_title},
            pages=True,
        )
        favicon_counts = await self._shared_counts(
            scope,
            Subdomain.favicon_hash,
            {s.favicon_hash for s in rows if s.favicon_hash},
        )
        render_counts = await self._render_counts(
            scope, {s.screenshot_phash for s in rows if s.screenshot_phash is not None}
        )
        findings = await self._findings_for(scope, [s.name for s in rows])
        endpoint_counts = await self._endpoint_counts(scope, [s.name for s in rows])
        evidence = await collect_evidence(self.session, scope, rows, node)
        names = await target_names(self.session, (s.target_id for s in rows))
        links = await CrossLinkService(self.session).for_rows(project_id, rows)
        items = []
        for s in rows:
            nums: set[int] = set()
            for ip in s.resolved_ips or []:
                nums |= ports_by_ip.get(ip, set())
            items.append(
                SubdomainRow(
                    **self._to_read(s).model_dump(),
                    target_value=names.get(s.target_id),
                    ports=sorted(nums, key=lambda n: (port_interest(n), n)),
                    endpoint_count=endpoint_counts.get(s.name, 0),
                    title_count=title_counts.get(s.page_title, _NO_SHARE)[0],
                    title_targets=title_counts.get(s.page_title, _NO_SHARE)[1],
                    favicon_count=favicon_counts.get(s.favicon_hash, _NO_SHARE)[0],
                    favicon_targets=favicon_counts.get(s.favicon_hash, _NO_SHARE)[1],
                    render_hash=(
                        hex_digest(s.screenshot_phash)
                        if s.screenshot_phash is not None
                        else None
                    ),
                    render_count=render_counts.get(s.screenshot_phash, _NO_SHARE)[0],
                    render_targets=render_counts.get(s.screenshot_phash, _NO_SHARE)[1],
                    vuln_count=findings.get(s.name, _NO_FINDINGS)[0],
                    vuln_severity=findings.get(s.name, _NO_FINDINGS)[1],
                    vuln_kev=findings.get(s.name, _NO_FINDINGS)[2],
                    vuln_severities=findings.get(s.name, _NO_FINDINGS)[3],
                    matched_in=evidence.get(s.id, []),
                    cross_links=links.get(s.id, []),
                )
            )
        return SubdomainSearchResult(
            items=items,
            total=min(total, COUNT_CAP) if capped else total,
            total_capped=capped,
        )

    async def _findings_for(
        self, scope: QueryScope, hosts: list[str]
    ) -> dict[str, tuple[int, str | None, bool, dict[str, int]]]:
        """Findings per host on this page."""
        if not hosts:
            return {}
        rows = await self.session.execute(
            select(
                Vulnerability.host,
                Vulnerability.severity,
                func.count(),
                func.bool_or(Vulnerability.is_kev),
            )
            .where(
                scope.match(Vulnerability.scan_id),
                Vulnerability.host.in_(hosts),
                not_(vuln_suppressed(scope)),
            )
            .group_by(Vulnerability.host, Vulnerability.severity)
        )
        by_host: dict[str, dict[str, int]] = {}
        kev_hosts: set[str] = set()
        for host, severity, count, kev in rows.all():
            if severity not in SEVERITY_ORDER:
                continue
            by_host.setdefault(host, {})[severity] = int(count)
            if kev:
                kev_hosts.add(host)
        return {
            host: (
                sum(counts.values()),
                min(counts, key=SEVERITY_ORDER.index),
                host in kev_hosts,
                {sev: counts[sev] for sev in SEVERITY_ORDER if sev in counts},
            )
            for host, counts in by_host.items()
        }

    async def counts(
        self, project_id: UUID, scope: ScopeLike, queries: list[str]
    ) -> QueryCounts:
        scope = QueryScope.of(scope)

        async def _build() -> QueryCounts:
            now = utc_now()
            base = select(Subdomain.id).where(
                Subdomain.project_id == project_id, scope.match(Subdomain.scan_id)
            )
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            ctx = QueryContext(scope=scope, now=now)
            try:
                return await count_queries(
                    self.session,
                    base,
                    queries,
                    lambda q: compile_query(parse_query(q), ctx),
                )
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("search counts failed", error=str(exc.orig))
                return QueryCounts()

        return await lead_cache.cached(
            self.session,
            name="counts:web_assets",
            scans=scope.ids,
            facets=f"{project_id}|{'|'.join(queries)}",
            model=QueryCounts,
            build=_build,
            keep=lambda computed: computed.computed,
        )

    async def tabs(
        self, project_id: UUID, scope: ScopeLike, f: SubdomainFilter
    ) -> QueryCounts:
        """Rows under each status tab, for the filter without its own statuses."""
        scope = QueryScope.of(scope)
        f = f.model_copy(update={"statuses": []})

        async def _build() -> QueryCounts:
            now = utc_now()
            base = self._scoped(project_id, scope, f, now, columns=(Subdomain.id,))
            try:
                predicate = compile_query(
                    parse_query(f.q), QueryContext(scope=scope, now=now)
                )
            except QuerySyntaxError:
                return QueryCounts()
            if predicate is not None:
                base = base.where(predicate)
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            tabs = {k: preds.status_class(k) for k in STATUS_CLASSES}
            try:
                return await count_named(self.session, base, {ALL_TAB: None, **tabs})
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("search tabs failed", error=str(exc.orig))
                return QueryCounts()

        return await lead_cache.cached(
            self.session,
            name="tabs:web_assets",
            scans=scope.ids,
            facets=f"{project_id}|{lead_cache.filter_of(f)}",
            model=QueryCounts,
            build=_build,
            keep=lambda counted: counted.computed,
            ttl=lead_cache.SEARCH_TTL_SECONDS,
            live_ttl=None,
        )

    async def leads(
        self, project_id: UUID, scope: ScopeLike, f: SubdomainFilter
    ) -> QueryLeads:
        scope = QueryScope.of(scope)

        async def _build() -> QueryLeads:
            now = utc_now()
            base = self._scoped(project_id, scope, f, now, columns=(Subdomain.id,))
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            try:
                ctx = QueryContext(scope=scope, now=now)
                return await build_leads(
                    self.session,
                    base,
                    HOST_QUERY.examples,
                    lambda q: compile_query(parse_query(q), ctx),
                    filtered=f.has_facets(),
                )
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("search leads failed", error=str(exc.orig))
                return QueryLeads()

        return await lead_cache.leads(
            self.session,
            dimension="web_assets",
            scans=scope.ids,
            facets=lead_cache.facets_of(f),
            build=_build,
        )

    async def seeds(
        self, project_id: UUID, scope: ScopeLike, f: SubdomainFilter, limit: int
    ) -> list[tuple[str, UUID]]:
        now = utc_now()
        scope = QueryScope.of(scope)
        base = self._scoped(
            project_id, scope, f, now, columns=(Subdomain.name, Subdomain.scan_id)
        )
        try:
            predicate = compile_query(
                parse_query(f.q), QueryContext(scope=scope, now=now)
            )
        except QuerySyntaxError:
            return []
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        rows = await self.session.execute(base.order_by(Subdomain.name).limit(limit))
        return [(name, scan_id) for name, scan_id in rows.all()]

    async def groups(
        self, project_id: UUID, scope: ScopeLike, f: SubdomainFilter, key: str
    ) -> QueryGroups:
        now = utc_now()
        scope = QueryScope.of(scope)
        base = self._scoped(project_id, scope, f, now, columns=(Subdomain.id,))
        try:
            node = parse_query(f.q)
            predicate = compile_query(node, QueryContext(scope=scope, now=now))
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            return await build_groups(self.session, base, key)
        except DBAPIError as exc:
            await self.session.rollback()
            logger.info("search groups failed", error=str(exc.orig))
            return QueryGroups(dimension=key)

    async def renders(
        self, project_id: UUID, scope: ScopeLike, f: SubdomainFilter
    ) -> RenderGroups:
        """Screenshot clusters over the filtered rows, one sample image each."""
        now = utc_now()
        scope = QueryScope.of(scope)
        base = select(Subdomain.id).where(
            Subdomain.project_id == project_id, scope.match(Subdomain.scan_id)
        )
        base = self._apply_filter(base, f, now, scope)
        try:
            node = parse_query(f.q)
            predicate = compile_query(node, QueryContext(scope=scope, now=now))
        except QuerySyntaxError as exc:
            return RenderGroups(error=syntax_error(exc))
        if predicate is not None:
            base = base.where(predicate)

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        scoped = base.subquery()
        rows = (
            await self.session.execute(
                select(
                    Subdomain.screenshot_phash,
                    func.count(func.distinct(Subdomain.id)),
                    func.mode().within_group(Subdomain.page_title),
                    func.min(Subdomain.name),
                    func.min(Subdomain.screenshot_path),
                )
                .select_from(Subdomain)
                .join(scoped, Subdomain.id == scoped.c.id)
                .where(Subdomain.screenshot_phash.isnot(None))
                .group_by(Subdomain.screenshot_phash)
            )
        ).all()
        histogram = {int(raw): int(n) for raw, n, _, _, _ in rows}
        detail = {int(raw): (title, name, path) for raw, _, title, name, path in rows}
        clusters = cluster(histogram)
        shared = {h for found in clusters if found.count > 1 for h in found.hashes}
        total = await self.session.scalar(select(func.count()).select_from(scoped))
        groups = [
            RenderGroup(
                hash=found.digest,
                label=detail[found.value][0],
                count=found.count,
                hosts=await self._render_hosts(scoped, found.hashes),
                screenshot_path=detail[found.value][2],
                query=f"screenshot:{found.digest}",
            )
            for found in clusters[:MAX_GROUPS]
        ]
        return RenderGroups(
            groups=groups,
            total_groups=len(clusters),
            grouped=sum(
                n for h, n in histogram.items() if is_identity(h) and h in shared
            ),
            ungrouped=sum(
                n for h, n in histogram.items() if is_identity(h) and h not in shared
            ),
            blank=sum(n for h, n in histogram.items() if not is_identity(h)),
            unrendered=int(total or 0) - sum(histogram.values()),
        )

    async def _render_hosts(self, scoped, hashes: tuple[int, ...]) -> list[str]:
        rows = await self.session.execute(
            select(Subdomain.name)
            .select_from(Subdomain)
            .join(scoped, Subdomain.id == scoped.c.id)
            .where(Subdomain.screenshot_phash.in_(hashes))
            .order_by(Subdomain.name)
            .limit(RENDER_SAMPLE_HOSTS)
        )
        return [name for (name,) in rows.all()]

    async def _render_counts(
        self, scope: QueryScope, values: set[int]
    ) -> dict[int, tuple[int, int]]:
        """How many rows in scope render like each of the page's own hashes."""
        if not values:
            return {}
        rows = await self.session.execute(
            select(
                Subdomain.screenshot_phash,
                func.count(),
                func.array_agg(distinct(Subdomain.target_id)),
            )
            .where(
                scope.match(Subdomain.scan_id),
                Subdomain.screenshot_phash.isnot(None),
            )
            .group_by(Subdomain.screenshot_phash)
        )
        histogram: dict[int, tuple[int, set]] = {
            int(raw): (int(n), set(targets or [])) for raw, n, targets in rows.all()
        }
        out: dict[int, tuple[int, int]] = {}
        for value in values:
            near = [
                found
                for other, found in histogram.items()
                if distance(value, other) <= SCREENSHOT_DISTANCE
            ]
            out[value] = (
                sum(n for n, _ in near),
                len({t for _, targets in near for t in targets}),
            )
        return out

    async def _endpoint_counts(
        self, scope: QueryScope, hosts: list[str]
    ) -> dict[str, int]:
        if not hosts:
            return {}
        rows = await self.session.execute(
            select(Endpoint.host, func.count())
            .where(scope.match(Endpoint.scan_id), Endpoint.host.in_(hosts))
            .group_by(Endpoint.host)
        )
        return {host: int(n) for host, n in rows.all()}

    async def _shared_counts(
        self, scope: QueryScope, col, values: set, *, pages: bool = False
    ) -> dict[object, tuple[int, int]]:
        """How many rows in scope carry each value, and how many targets they sit under."""
        if not values:
            return {}
        rows = await self.session.execute(
            select(
                col,
                func.count(),
                func.count(distinct(Subdomain.target_id)),
                func.array_agg(distinct(Subdomain.http_status)),
            )
            .where(scope.match(Subdomain.scan_id), col.in_(values))
            .group_by(col)
        )
        return {
            value: (int(n), int(targets))
            for value, n, targets, statuses in rows.all()
            if not (pages and generic_page(str(value), statuses or []))
        }

    async def facets(self, project_id: UUID, scope: ScopeLike) -> SubdomainFacets:
        now = utc_now()
        scope = QueryScope.of(scope)
        reach = (Subdomain.project_id == project_id, scope.match(Subdomain.scan_id))

        status_key = case(
            (Subdomain.http_status.is_(None), "none"),
            *[
                (
                    and_(Subdomain.http_status >= lo, Subdomain.http_status < hi),
                    bucket,
                )
                for bucket, (lo, hi) in preds.STATUS_BUCKETS.items()
            ],
            else_=None,
        )
        status_rows = await self.session.execute(
            select(status_key.label("k"), func.count())
            .where(*reach)
            .group_by(status_key)
        )
        order = list(preds.STATUS_LABELS)
        status_map = {k: c for k, c in status_rows.all() if k is not None}
        status = [
            Facet(value=k, label=preds.STATUS_LABELS[k], count=status_map[k])
            for k in order
            if k in status_map
        ]

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
                .where(*reach)
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

        tech = await self._json_facet("tech", project_id, scope)
        source = await self._json_facet("sources", project_id, scope)
        hygiene_rows = await self.session.execute(
            select(
                *[
                    func.count().filter(preds.hygiene_check(key)).label(key)
                    for key in hygiene_defs.CHECK_KEYS
                ]
            )
            .select_from(Subdomain)
            .where(*reach)
        )
        hygiene_counts = hygiene_rows.one()._mapping
        hygiene = [
            Facet(
                value=spec.key,
                label=spec.label,
                count=int(hygiene_counts[spec.key]),
            )
            for spec in hygiene_defs.CHECKS
            if hygiene_counts[spec.key] > 0
        ]

        posture_rows = await self.session.execute(
            select(
                *[
                    func.count().filter(preds.posture_check(key)).label(key)
                    for key in posture_defs.CHECK_KEYS
                ]
            )
            .select_from(Subdomain)
            .where(*reach)
        )
        posture_counts = posture_rows.one()._mapping
        posture = [
            Facet(
                value=spec.key,
                label=spec.label,
                count=int(posture_counts[spec.key]),
            )
            for spec in posture_defs.CHECKS
            if posture_counts[spec.key] > 0
        ]

        service_rows = await self.session.execute(
            select(Port.service_name, func.count())
            .where(
                Port.project_id == project_id,
                scope.match(Port.scan_id),
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
            status=status,
            tech=tech,
            service=service,
            source=source,
            cert=cert,
            hygiene=hygiene,
            posture=posture,
        )

    async def hygiene(self, project_id: UUID, scope: ScopeLike) -> HygieneSummary:
        """Hosts failing each check, over the hosts it applied to."""
        scope = QueryScope.of(scope)
        reach = (Subdomain.project_id == project_id, scope.match(Subdomain.scan_id))
        issues = cast(Subdomain.hygiene_issues, JSONB)
        checked = cast(Subdomain.hygiene_checked, JSONB)
        columns = [
            func.count().label("hosts"),
            func.count()
            .filter(Subdomain.hygiene_checked.isnot(None))
            .label("evaluated"),
            func.count()
            .filter(
                and_(
                    Subdomain.http_status.isnot(None),
                    Subdomain.hygiene_checked.is_(None),
                )
            )
            .label("pending"),
            func.count()
            .filter(
                and_(
                    func.jsonb_array_length(checked) > 0,
                    func.jsonb_array_length(issues) == 0,
                )
            )
            .label("clean"),
            func.count()
            .filter(preds.hygiene([hygiene_defs.TONE_WARNING]))
            .label("warning"),
            func.count().filter(preds.hygiene([hygiene_defs.TONE_INFO])).label("info"),
        ]
        for key in hygiene_defs.CHECK_KEYS:
            columns.append(
                func.count().filter(preds.hygiene_check(key)).label(f"f_{key}")
            )
            columns.append(
                func.count().filter(preds.hygiene_applies(key)).label(f"a_{key}")
            )
        row = (
            (
                await self.session.execute(
                    select(*columns).select_from(Subdomain).where(*reach)
                )
            )
            .one()
            ._mapping
        )
        return HygieneSummary(
            hosts=int(row["hosts"]),
            evaluated=int(row["evaluated"]),
            pending=int(row["pending"]),
            clean=int(row["clean"]),
            warning=int(row["warning"]),
            info=int(row["info"]),
            checks=[
                HygieneCheckCount(
                    key=spec.key,
                    failing=int(row[f"f_{spec.key}"]),
                    applicable=int(row[f"a_{spec.key}"]),
                    query=spec.query,
                )
                for spec in hygiene_defs.CHECKS
            ],
        )

    async def posture(self, project_id: UUID, scope: ScopeLike) -> HygieneSummary:
        """Hosts whose zone fails each check, over the hosts it applied to."""
        scope = QueryScope.of(scope)
        reach = (Subdomain.project_id == project_id, scope.match(Subdomain.scan_id))
        issues = cast(Subdomain.posture_issues, JSONB)
        checked = cast(Subdomain.posture_checked, JSONB)
        columns = [
            func.count().label("hosts"),
            func.count()
            .filter(Subdomain.posture_checked.isnot(None))
            .label("evaluated"),
            func.count().filter(Subdomain.posture_checked.is_(None)).label("pending"),
            func.count()
            .filter(
                and_(
                    func.jsonb_array_length(checked) > 0,
                    func.jsonb_array_length(issues) == 0,
                )
            )
            .label("clean"),
            func.count().filter(preds.posture([TONE_WARNING])).label("warning"),
            func.count().filter(preds.posture([TONE_INFO])).label("info"),
        ]
        for key in posture_defs.CHECK_KEYS:
            columns.append(
                func.count().filter(preds.posture_check(key)).label(f"f_{key}")
            )
            columns.append(
                func.count().filter(preds.posture_applies(key)).label(f"a_{key}")
            )
        rows = (
            select(
                cast(Subdomain.posture_issues, JSONB).label("posture_issues"),
                cast(Subdomain.posture_checked, JSONB).label("posture_checked"),
            )
            .where(*reach)
            .cte("posture_rows")
            .prefix_with("MATERIALIZED")
        )
        adapter = ClauseAdapter(rows, adapt_on_names=True)
        row = (
            (
                await self.session.execute(
                    select(*(adapter.traverse(c) for c in columns)).select_from(rows)
                )
            )
            .one()
            ._mapping
        )
        return HygieneSummary(
            hosts=int(row["hosts"]),
            evaluated=int(row["evaluated"]),
            pending=int(row["pending"]),
            clean=int(row["clean"]),
            warning=int(row["warning"]),
            info=int(row["info"]),
            checks=[
                HygieneCheckCount(
                    key=spec.key,
                    failing=int(row[f"f_{spec.key}"]),
                    applicable=int(row[f"a_{spec.key}"]),
                    query=spec.query,
                )
                for spec in posture_defs.CHECKS
            ],
        )

    async def _json_facet(
        self,
        column: str,
        project_id: UUID,
        scope: ScopeLike,
        *,
        limit: int = _FACET_LIMIT,
        search: str | None = None,
    ) -> list[Facet]:
        sids = list(QueryScope.of(scope).ids)
        if search:
            stmt = _FACET_SEARCH_SQL[column].bindparams(
                pid=project_id, sids=sids, lim=limit, q=f"%{search}%"
            )
        else:
            stmt = _FACET_SQL[column].bindparams(pid=project_id, sids=sids, lim=limit)
        rows = await self.session.execute(stmt)
        return [Facet(value=v, label=v, count=c) for v, c in rows.all()]

    async def tech(
        self, project_id: UUID, scan_id: UUID, search: str | None, limit: int
    ) -> list[Facet]:
        return await self._json_facet(
            "tech", project_id, scan_id, limit=min(limit, _TECH_LIMIT), search=search
        )

    async def related(
        self, project_id: UUID, scope: ScopeLike, name: str
    ) -> list[SubdomainRelation]:
        """Every hub this host is a member of, over the scope the page is showing."""
        scope = QueryScope.of(scope)
        subject = (
            (
                await self.session.execute(
                    select(Subdomain).where(
                        Subdomain.project_id == project_id,
                        scope.match(Subdomain.scan_id),
                        Subdomain.name == name,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not subject:
            return []
        assets = (
            (
                await self.session.execute(
                    select(HttpAsset).where(
                        scope.match(HttpAsset.scan_id), HttpAsset.host == name
                    )
                )
            )
            .scalars()
            .all()
        )
        wanted = values_carried(subject, assets)
        if not wanted:
            return []
        found = await CorrelationFinder(self.session).find(scope, values=wanted)
        mine = {row.id for row in subject}
        out = []
        for hub in found.hubs:
            if hub.platform or hub.common:
                continue
            if not any(m.id in mine for m in hub.members):
                continue
            peers = list(
                dict.fromkeys(
                    m.name for m in hub.members if m.id not in mine and m.name != name
                )
            )
            if not peers:
                continue
            out.append(
                SubdomainRelation(
                    kind=hub.kind,
                    reason=CORRELATION_RELATION_PHRASE[hub.kind],
                    value=hub.value,
                    label=CORRELATION_KIND_LABELS[hub.kind],
                    query=hub.query,
                    targets=hub.targets,
                    hosts=peers[:_RELATION_CAP],
                    total=len(peers),
                )
            )
        order = {kind: i for i, kind in enumerate(CORRELATION_KIND_ORDER)}
        out.sort(key=lambda r: (order.get(r.kind, len(order)), -r.targets, -r.total))
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
        live = preds.live()

        counts = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count().filter(live).label("live"),
                    func.count().filter(preds.answered()).label("web"),
                    func.count().filter(preds.resolved()).label("resolved"),
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
                    .filter(
                        func.jsonb_array_length(cast(Subdomain.sources, JSONB)) == 1
                    )
                    .label("single_source"),
                    func.count()
                    .filter(Subdomain.http_status >= preds.HTTP_SERVER)
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
                            Subdomain.http_status.in_(preds.AUTH_STATUS),
                            Subdomain.page_title.op("~*")(preds.AUTH_RE),
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
            .where(*scope, preds.port_match(Port.number.in_(SENSITIVE_PORTS), scan_id))
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
            SurfaceStat(key="subdomains", label="Web assets", value=counts.total),
            SurfaceStat(
                key="resolved",
                label="Resolved",
                value=counts.resolved,
                filter="is:resolved",
            ),
            SurfaceStat(key="live", label="Live", value=counts.live, filter="is:live"),
            SurfaceStat(key="web", label="With web", value=counts.web, filter="is:web"),
            SurfaceStat(key="ips", label="Unique IPs", value=int(ip_total or 0)),
            SurfaceStat(key="asns", label="Networks", value=int(asn_total or 0)),
            SurfaceStat(key="ports", label="Open ports", value=int(port_total or 0)),
        ]

        raw_attention = [
            (
                "expired",
                "Expired certificates",
                counts.expired,
                "cert:expired",
                "destructive",
            ),
            (
                "takeover",
                "Dangling CNAME records",
                counts.cname_only,
                "cname:. and not is:resolved",
                "destructive",
            ),
            (
                "expiring",
                "Certificates expiring within 30 days",
                counts.expiring,
                "cert:expiring",
                "warning",
            ),
            (
                "selfsigned",
                "Self-signed certificates",
                counts.self_signed,
                "cert:self-signed",
                "warning",
            ),
            (
                "nowaf",
                "Live web assets without a CDN or WAF",
                counts.nowaf,
                "is:live waf:none cdn:no",
                "warning",
            ),
            (
                "server",
                "Web assets returning server errors",
                counts.server_err,
                "status:5xx",
                "destructive",
            ),
            ("auth", "Login or admin panels", counts.auth, "is:auth", "warning"),
            (
                "sensitive",
                "Web assets with a sensitive service",
                int(sensitive or 0),
                "is:sensitive",
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
            (Subdomain.http_status < preds.HTTP_REDIRECT, "live"),
            (Subdomain.http_status < preds.HTTP_CLIENT, "redirect"),
            (Subdomain.http_status.in_(preds.AUTH_STATUS), "auth"),
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
            (Subdomain.tls_not_after < now + timedelta(days=7), "week"),
            (Subdomain.tls_not_after < now + timedelta(days=30), "month"),
            (Subdomain.tls_not_after < now + timedelta(days=90), "quarter"),
            (Subdomain.tls_not_after.isnot(None), "later"),
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
                _DISTINCT_SQL["tech"].bindparams(pid=project_id, sids=[scan_id])
            )
            or 0
        )
        geo_rows = await self.session.execute(
            select(IpAddress.country, func.count())
            .where(
                IpAddress.project_id == project_id,
                IpAddress.scan_id == scan_id,
                IpAddress.country.isnot(None),
            )
            .group_by(IpAddress.country)
            .order_by(func.count().desc())
        )
        geography = [Tally(name=c, count=n) for c, n in geo_rows.all()]
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
            select(HttpAsset.tls_subject_cn, func.count(distinct(HttpAsset.host)))
            .where(
                HttpAsset.project_id == project_id,
                HttpAsset.scan_id == scan_id,
                HttpAsset.tls_subject_cn.isnot(None),
            )
            .group_by(HttpAsset.tls_subject_cn)
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
            single_source=counts.single_source,
            resolution=resolution,
            status_reframe=status_reframe,
            cert_buckets=cert_buckets,
            top_tech=top_tech,
            tech_total=tech_total,
            geography=geography,
            geo_total=sum(t.count for t in geography),
            clusters=clusters[:_CLUSTER_LIMIT],
        )

    @staticmethod
    def _asset_rank(a: HttpAsset) -> tuple:
        alive = (
            a.status_code is not None
            and preds.HTTP_OK <= a.status_code < preds.HTTP_CLIENT
        )
        return (a.scheme == "https", alive, a.port in (443, 80), -(a.port or 0))

    async def correlation(
        self, project_id: UUID, scope: ScopeLike, name: str
    ) -> SubdomainCorrelation:
        scope = QueryScope.of(scope)
        sub = await self.session.scalar(
            select(Subdomain).where(
                Subdomain.project_id == project_id,
                scope.match(Subdomain.scan_id),
                Subdomain.name == name,
            )
        )
        ips = list(sub.resolved_ips or []) if sub else []
        ha = HttpAssetService(self.session)
        asset_rows = (
            (
                await self.session.execute(
                    select(HttpAsset)
                    .where(scope.match(HttpAsset.scan_id), HttpAsset.host == name)
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
                        .where(scope.match(Port.scan_id), Port.ip.in_(ips))
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
                            scope.match(IpAddress.scan_id), IpAddress.ip.in_(ips)
                        )
                    )
                )
                .scalars()
                .all()
            )
            isvc = IpAddressService(self.session)
            ip_metas = [isvc._to_read(i) for i in ip_rows]

        return SubdomainCorrelation(
            primary_asset=ha._to_read(primary) if primary else None,
            services=services,
            ports=ports,
            ip_metas=ip_metas,
            related=await self.related(project_id, scope, name),
        )
