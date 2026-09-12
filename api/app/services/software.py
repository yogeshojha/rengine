from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    SoftwareQueryContext,
    compile_software_query,
    parse_query,
    query_error_for,
    software_has_baseline,
)
from app.services.target_names import target_names
from shared.definitions.asset_query import COUNT_CAP, SOFTWARE_QUERY
from shared.definitions.evidence import EVIDENCE_LABELS, EVIDENCE_ORDER
from shared.definitions.software import (
    CAVEAT_LABELS,
    CAVEAT_ORDER,
    CONFIDENCE_LABELS,
    CONFIDENCE_ORDER,
    PRODUCTS_BY_KEY,
    VERSION_SOURCE_LABELS,
    VersionSource,
)
from shared.definitions.threat_intel import STALE_AFTER_HOURS, FeedKind, exploit_band
from shared.definitions.vulnerabilities import SEVERITY_LABELS, SEVERITY_ORDER
from shared.logging import get_logger
from shared.models.asset_query import QueryError
from shared.models.software import (
    NvdCve,
    SoftwareComponentRead,
    SoftwareCoverage,
    SoftwareCve,
    SoftwareCveRead,
    SoftwareFacet,
    SoftwareFacets,
    SoftwareFilter,
    SoftwarePage,
)
from shared.models.threat_intel import ThreatFeed
from shared.services.asset_query import lead_cache
from shared.utils.datetime import utc_now
from shared.utils.software import normalize_product

logger = get_logger(__name__)

_FACET_LIMIT = 20
_UNMAPPED_SHOWN = 25
_SORTS = {
    "rank": SoftwareCve.exploit_score,
    "cvss": SoftwareCve.cvss_score,
    "epss": SoftwareCve.epss_score,
    "cve": SoftwareCve.cve,
    "software": SoftwareCve.name,
    "host": SoftwareCve.host,
    "seen": SoftwareCve.discovered_at,
}


def _severity_rank():
    return func.coalesce(SoftwareCve.cvss_score, 0.0)


class SoftwareService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _context(self, scope: QueryScope, now: datetime) -> SoftwareQueryContext:
        return SoftwareQueryContext(scope=scope, now=now)

    def _scoped(self, scope: QueryScope):
        return select(SoftwareCve).where(scope.match(SoftwareCve.scan_id))

    def _order(self, base, f: SoftwareFilter):
        column = _SORTS.get((f.sort or "").lower())
        descending = (f.direction or "desc").lower() != "asc"
        if column is None:
            return base.order_by(
                SoftwareCve.exploit_score.desc(),
                _severity_rank().desc(),
                SoftwareCve.cve.desc(),
                SoftwareCve.id,
            )
        ordered = column.desc() if descending else column.asc()
        return base.order_by(ordered, SoftwareCve.cve, SoftwareCve.id)

    async def search(self, scope: ScopeLike, f: SoftwareFilter) -> SoftwarePage:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope)
        try:
            predicate = compile_software_query(
                parse_query(f.q, SOFTWARE_QUERY), self._context(scope, now)
            )
        except QuerySyntaxError as exc:
            return SoftwarePage(
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
        seen = await self._seen_before(scope, [row.fingerprint for row in rows])
        baseline = await self.session.scalar(select(software_has_baseline(scope)))
        for row in rows:
            page.items.append(
                self._to_read(
                    row,
                    target_value=names.get(row.target_id),
                    description=descriptions.get(row.cve),
                    is_new=bool(baseline) and row.fingerprint not in seen,
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

    async def _seen_before(
        self, scope: QueryScope, fingerprints: list[str]
    ) -> set[str]:
        if not fingerprints or not scope.ids:
            return set()
        rows = await self.session.execute(
            text(
                "SELECT DISTINCT e.fingerprint FROM software_cves e "
                "JOIN software_cves cur ON cur.scan_id = ANY(:sids) "
                "AND cur.fingerprint = e.fingerprint "
                "WHERE e.target_id = cur.target_id AND NOT (e.scan_id = ANY(:sids)) "
                "AND e.discovered_at < cur.discovered_at AND e.fingerprint = ANY(:fps)"
            ),
            {"sids": [str(i) for i in scope.ids], "fps": fingerprints},
        )
        return {row[0] for row in rows.all()}

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
        rows = await self.session.execute(
            select(column, func.count())
            .where(scope.match(SoftwareCve.scan_id))
            .group_by(column)
            .order_by(func.count().desc())
            .limit(_FACET_LIMIT)
        )
        found = [
            SoftwareFacet(key=key, label=labels.get(key, key), count=count)
            for key, count in rows.all()
            if key
        ]
        if not order:
            return found
        rank = {key: index for index, key in enumerate(order)}
        return sorted(found, key=lambda item: rank.get(item.key, len(rank)))

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
            feed = await self.session.scalar(
                select(ThreatFeed).where(ThreatFeed.kind == FeedKind.NVD.value)
            )
            age = None
            if feed is not None and feed.last_synced_at is not None:
                age = (utc_now() - feed.last_synced_at).total_seconds() / 3600
            mapped, unmapped, names = await self._components(scope)
            matched = await self.session.scalar(
                text(
                    "SELECT count(DISTINCT coalesce(http_asset_id::text, port_id::text)) "
                    "FROM software_cves WHERE scan_id = ANY(:sids)"
                ).bindparams(sids=[str(i) for i in scope.ids])
            )
            findings = await self.session.scalar(
                select(func.count()).where(scope.match(SoftwareCve.scan_id))
            )
            return SoftwareCoverage(
                components=mapped + unmapped,
                mapped=mapped,
                unmapped=unmapped,
                unmapped_names=names,
                matched=int(matched or 0),
                findings=int(findings or 0),
                feed_ready=feed is not None and feed.rows > 0,
                feed_age_hours=age,
                stale=age is not None and age > STALE_AFTER_HOURS,
            )

        return await lead_cache.cached(
            self.session,
            name="software:coverage",
            scans=scope.ids,
            facets="",
            model=SoftwareCoverage,
            build=build,
        )

    async def _components(
        self, scope: QueryScope
    ) -> tuple[int, int, list[SoftwareComponentRead]]:
        """Counted the way the matcher resolves them, so the two never disagree."""
        if not scope.ids:
            return 0, 0, []
        sids = [str(i) for i in scope.ids]
        rows = await self.session.execute(
            text(
                "SELECT value ->> 'name' AS name, value ->> 'source' AS source, "
                "count(*) AS n FROM http_assets, json_array_elements(software) value "
                "WHERE scan_id = ANY(:sids) GROUP BY 1, 2"
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
        missing: dict[tuple[str, str], int] = {}
        counted: list[tuple[str, str, int]] = [
            (row.name, row.source or VersionSource.FINGERPRINT.value, row.n)
            for row in rows.all()
            if row.name
        ]
        counted += [
            (row.name, VersionSource.BANNER.value, row.n)
            for row in ports.all()
            if row.name
        ]
        for name, source, count in counted:
            if normalize_product(name) in PRODUCTS_BY_KEY:
                mapped += count
            else:
                unmapped += count
                missing[(name, source)] = missing.get((name, source), 0) + count
        ordered = sorted(missing.items(), key=lambda item: -item[1])[:_UNMAPPED_SHOWN]
        return (
            mapped,
            unmapped,
            [
                SoftwareComponentRead(
                    name=name, version_source=source, mapped=False, assets=count
                )
                for (name, source), count in ordered
            ],
        )

    async def counts(self, scope: ScopeLike, queries: list[str]) -> dict[str, int]:
        scope = QueryScope.of(scope)
        now = utc_now()
        out: dict[str, int] = {}
        for query in queries:
            base = self._scoped(scope)
            try:
                predicate = compile_software_query(
                    parse_query(query, SOFTWARE_QUERY), self._context(scope, now)
                )
            except QuerySyntaxError:
                out[query] = 0
                continue
            if predicate is not None:
                base = base.where(predicate)
            counted = await self.session.scalar(
                select(func.count()).select_from(base.subquery())
            )
            out[query] = int(counted or 0)
        return out

    async def scan_total(self, scan_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count()).where(SoftwareCve.scan_id == scan_id)
            )
            or 0
        )
