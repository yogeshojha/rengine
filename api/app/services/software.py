from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.baseline import new_row_ids
from app.services.facets import column_facet
from app.services.target_names import target_names
from shared.definitions.asset_query import COUNT_CAP, SOFTWARE_QUERY
from shared.definitions.evidence import EVIDENCE_LABELS, EVIDENCE_ORDER
from shared.definitions.software import (
    CAVEAT_LABELS,
    CAVEAT_ORDER,
    CONFIDENCE_LABELS,
    CONFIDENCE_ORDER,
    MAX_MATCHES_PER_SCAN,
    PRODUCTS_BY_KEY,
    VERSION_SOURCE_LABELS,
)
from shared.definitions.threat_intel import STALE_AFTER_HOURS, FeedKind, exploit_band
from shared.definitions.vulnerabilities import SEVERITY_LABELS, SEVERITY_ORDER
from shared.logging import get_logger
from shared.models.asset_query import QueryCounts
from shared.models.software import (
    NvdCve,
    SoftwareCoverage,
    SoftwareCve,
    SoftwareCveRead,
    SoftwareFacet,
    SoftwareFacets,
    SoftwareFilter,
    SoftwarePage,
)
from shared.models.threat_intel import ThreatFeed
from shared.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    SoftwareQueryContext,
    compile_software_query,
    count_queries,
    lead_cache,
    parse_query,
    query_error_for,
    software_is_new,
    syntax_error,
)
from shared.services.surface_query import software as surface_software
from shared.services.threat_intel import feed_age_hours
from shared.utils.datetime import utc_now
from shared.utils.software import normalize_product

logger = get_logger(__name__)

_FACET_LIMIT = 20


class SoftwareService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _context(self, scope: QueryScope, now: datetime) -> SoftwareQueryContext:
        return SoftwareQueryContext(scope=scope, now=now)

    def _scoped(self, scope: QueryScope):
        return surface_software.scoped(scope, SoftwareFilter())

    def _order(self, base, f: SoftwareFilter):
        return surface_software.order(base, f)

    async def search(self, scope: ScopeLike, f: SoftwareFilter) -> SoftwarePage:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope)
        try:
            predicate = compile_software_query(
                parse_query(f.q, SOFTWARE_QUERY), self._context(scope, now)
            )
        except QuerySyntaxError as exc:
            return SoftwarePage(error=syntax_error(exc))
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
                        self._order(base, f).limit(f.limit).offset(f.offset)
                    )
                )
                .scalars()
                .all()
            )
        except DBAPIError as exc:
            await self.session.rollback()
            rejected = query_error_for(exc)
            if rejected is None:
                raise
            logger.info("software query rejected", error=str(exc.orig))
            return SoftwarePage(error=rejected)

        total = int(counted or 0)
        capped = total > COUNT_CAP
        page = SoftwarePage(
            total=min(total, COUNT_CAP) if capped else total, total_capped=capped
        )
        if not rows:
            return page

        names = await target_names(self.session, (row.target_id for row in rows))
        descriptions = await self._descriptions([row.cve for row in rows])
        new_ids = await new_row_ids(
            self.session,
            SoftwareCve.id,
            software_is_new(scope),
            [row.id for row in rows],
        )
        for row in rows:
            page.items.append(
                self._to_read(
                    row,
                    target_value=names.get(row.target_id),
                    description=descriptions.get(row.cve),
                    is_new=row.id in new_ids,
                )
            )
        return page

    def _to_read(
        self,
        row: SoftwareCve,
        *,
        target_value: str | None,
        description: str | None,
        is_new: bool,
    ) -> SoftwareCveRead:
        return SoftwareCveRead(
            id=row.id,
            scan_id=row.scan_id,
            target_id=row.target_id,
            target_value=target_value,
            cve=row.cve,
            name=row.name,
            version=row.version,
            vendor=row.vendor,
            product=row.product,
            cpe=row.cpe,
            version_source=row.version_source,
            version_source_label=VERSION_SOURCE_LABELS.get(row.version_source, ""),
            severity=row.severity,
            cvss_score=row.cvss_score,
            epss_score=row.epss_score,
            epss_percentile=row.epss_percentile,
            band=exploit_band(row.epss_score),
            is_kev=row.is_kev,
            kev_ransomware=row.kev_ransomware,
            kev_due_date=row.kev_due_date,
            exploit_score=row.exploit_score,
            intel_kinds=list(row.intel_kinds or []),
            confidence=row.confidence,
            confidence_label=CONFIDENCE_LABELS.get(row.confidence, ""),
            caveats=[
                {
                    "kind": kind,
                    "label": CAVEAT_LABELS.get(kind, kind),
                }
                for kind in (row.caveats or [])
            ],
            evidence=row.evidence,
            evidence_label=EVIDENCE_LABELS.get(row.evidence, ""),
            fixed_in=row.fixed_in,
            fixed_in_assets=row.fixed_in_assets,
            description=description,
            host=row.host,
            ip=row.ip,
            port=row.port,
            url=row.url,
            http_asset_id=row.http_asset_id,
            port_id=row.port_id,
            discovered_at=row.discovered_at,
            is_new=is_new,
        )

    async def _descriptions(self, cves: list[str]) -> dict[str, str]:
        if not cves:
            return {}
        rows = await self.session.execute(
            select(NvdCve.cve, NvdCve.description).where(NvdCve.cve.in_(set(cves)))
        )
        return {cve: description for cve, description in rows.all() if description}

    async def counts(self, scope: ScopeLike, queries: list[str]) -> QueryCounts:
        scope = QueryScope.of(scope)

        async def _build() -> QueryCounts:
            ctx = self._context(scope, utc_now())
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            try:
                return await count_queries(
                    self.session,
                    self._scoped(scope),
                    queries,
                    lambda q: compile_software_query(
                        parse_query(q, SOFTWARE_QUERY), ctx
                    ),
                )
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("software counts failed", error=str(exc.orig))
                return QueryCounts()

        return await lead_cache.cached(
            self.session,
            name="counts:software",
            scans=scope.ids,
            facets="|".join(queries),
            model=QueryCounts,
            build=_build,
            keep=lambda counted: counted.computed,
            live_ttl=None,
        )

    async def facets(self, scope: ScopeLike) -> SoftwareFacets:
        scope = QueryScope.of(scope)

        async def build() -> SoftwareFacets:
            return SoftwareFacets(
                severity=await self._facet(
                    scope, SoftwareCve.severity, SEVERITY_LABELS, SEVERITY_ORDER
                ),
                confidence=await self._facet(
                    scope, SoftwareCve.confidence, CONFIDENCE_LABELS, CONFIDENCE_ORDER
                ),
                source=await self._facet(
                    scope,
                    SoftwareCve.version_source,
                    VERSION_SOURCE_LABELS,
                    tuple(VERSION_SOURCE_LABELS),
                ),
                caveat=await self._caveat_facet(scope),
                evidence=await self._facet(
                    scope, SoftwareCve.evidence, EVIDENCE_LABELS, EVIDENCE_ORDER
                ),
                product=await self._facet(scope, SoftwareCve.name, {}, ()),
            )

        return await lead_cache.cached(
            self.session,
            name="software:facets",
            scans=scope.ids,
            facets="",
            model=SoftwareFacets,
            build=build,
        )

    async def _facet(
        self, scope: QueryScope, column, labels: dict[str, str], order: tuple[str, ...]
    ) -> list[SoftwareFacet]:
        return await column_facet(
            self.session,
            scope,
            column,
            SoftwareCve.scan_id,
            labels=labels,
            order=order,
            make=SoftwareFacet,
            limit=_FACET_LIMIT,
        )

    async def _caveat_facet(self, scope: QueryScope) -> list[SoftwareFacet]:
        rows = await self.session.execute(
            text(
                "SELECT value, count(*) FROM software_cves, "
                "json_array_elements_text(caveats) value "
                "WHERE scan_id = ANY(:sids) GROUP BY value"
            ),
            {"sids": [str(i) for i in scope.ids]},
        )
        counts = dict(rows.all())
        return [
            SoftwareFacet(key=kind, label=CAVEAT_LABELS[kind], count=counts[kind])
            for kind in CAVEAT_ORDER
            if kind in counts
        ]

    async def coverage(self, scope: ScopeLike) -> SoftwareCoverage:
        scope = QueryScope.of(scope)

        async def build() -> SoftwareCoverage:
            mapped, unmapped = await self._components(scope)
            matched = await self.session.scalar(
                text(
                    "SELECT count(DISTINCT coalesce(http_asset_id::text, port_id::text)) "
                    "FROM software_cves WHERE scan_id = ANY(:sids)"
                ).bindparams(sids=[str(i) for i in scope.ids])
            )
            per_scan = (
                await self.session.execute(
                    select(func.count())
                    .where(scope.match(SoftwareCve.scan_id))
                    .group_by(SoftwareCve.scan_id)
                )
            ).scalars()
            stored = [int(n) for n in per_scan]
            return SoftwareCoverage(
                components=mapped + unmapped,
                mapped=mapped,
                unmapped=unmapped,
                matched=int(matched or 0),
                findings=sum(stored),
                capped_at=MAX_MATCHES_PER_SCAN
                if any(n >= MAX_MATCHES_PER_SCAN for n in stored)
                else None,
            )

        counts = await lead_cache.cached(
            self.session,
            name="software:coverage",
            scans=scope.ids,
            facets="",
            model=SoftwareCoverage,
            build=build,
        )
        feed = await self.session.scalar(
            select(ThreatFeed).where(ThreatFeed.kind == FeedKind.NVD.value)
        )
        age = feed_age_hours(feed)
        return counts.model_copy(
            update={
                "feed_ready": feed is not None and feed.rows > 0,
                "feed_age_hours": age,
                "stale": age is not None and age > STALE_AFTER_HOURS,
            }
        )

    async def _components(self, scope: QueryScope) -> tuple[int, int]:
        """Versioned components, mapped and unmapped."""
        if not scope.ids:
            return 0, 0
        sids = [str(i) for i in scope.ids]
        rows = await self.session.execute(
            text(
                "SELECT value ->> 'name' AS name, count(*) AS n "
                "FROM http_assets, json_array_elements(software) value "
                "WHERE scan_id = ANY(:sids) GROUP BY 1"
            ).bindparams(sids=sids)
        )
        ports = await self.session.execute(
            text(
                "SELECT product AS name, count(*) AS n FROM ports "
                "WHERE scan_id = ANY(:sids) AND product IS NOT NULL "
                "AND version IS NOT NULL AND version <> '' GROUP BY 1"
            ).bindparams(sids=sids)
        )
        mapped = 0
        unmapped = 0
        for row in [*rows.all(), *ports.all()]:
            if not row.name:
                continue
            if normalize_product(row.name) in PRODUCTS_BY_KEY:
                mapped += row.n
            else:
                unmapped += row.n
        return mapped, unmapped
