from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    SecretQueryContext,
    build_secret_groups,
    compile_secret_query,
    parse_query,
    query_error_for,
    secret_has_baseline,
)
from app.services.target_names import target_names
from shared.definitions.asset_query import COUNT_CAP, SECRET_QUERY
from shared.definitions.secrets import (
    DETECTORS_BY_KEY,
    GROUP_LABELS,
    GROUP_ORDER,
    MAX_SIGHTINGS_SHOWN,
    MINER_SOURCE_LABELS,
    SOURCE_LABELS,
    STATE_LABELS,
    STATE_ORDER,
    SecretState,
)
from shared.definitions.vulnerabilities import CoverageStatus
from shared.logging import get_logger
from shared.models.asset_query import QueryError, QueryGroups
from shared.models.secret import (
    Secret,
    SecretCoverage,
    SecretCoverageRead,
    SecretCoverageRow,
    SecretDetail,
    SecretFacet,
    SecretFacets,
    SecretFilter,
    SecretPage,
    SecretRead,
    SecretSighting,
    SecretSightingRead,
)
from shared.services.asset_query import lead_cache
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 20
_SORTS = {
    "kind": Secret.kind,
    "hosts": Secret.hosts,
    "sightings": Secret.sightings,
    "seen": Secret.discovered_at,
}
# exposed, expired, public
_STATE_RANK = case(
    {
        SecretState.EXPOSED.value: 3,
        SecretState.EXPIRED.value: 2,
        SecretState.PUBLIC.value: 1,
    },
    value=Secret.state,
    else_=0,
)


class SecretService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _context(self, scope: QueryScope, now: datetime) -> SecretQueryContext:
        return SecretQueryContext(scope=scope, now=now)

    def _scoped(self, scope: QueryScope):
        return select(Secret).where(scope.match(Secret.scan_id))

    def _order(self, base, f: SecretFilter):
        key = (f.sort or "state").lower()
        descending = (f.direction or "desc").lower() != "asc"
        if key == "state":
            rank = _STATE_RANK.desc() if descending else _STATE_RANK.asc()
            return base.order_by(
                rank, Secret.hosts.desc(), Secret.discovered_at.desc(), Secret.id
            )
        column = _SORTS.get(key)
        if column is None:
            return base.order_by(
                _STATE_RANK.desc(),
                Secret.hosts.desc(),
                Secret.discovered_at.desc(),
                Secret.id,
            )
        ordered = column.desc() if descending else column.asc()
        return base.order_by(ordered, Secret.discovered_at.desc(), Secret.id)

    async def search(self, scope: ScopeLike, f: SecretFilter) -> SecretPage:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope)
        try:
            predicate = compile_secret_query(
                parse_query(f.q, SECRET_QUERY), self._context(scope, now)
            )
        except QuerySyntaxError as exc:
            return SecretPage(
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
            logger.info("secret query rejected", error=str(exc.orig))
            return SecretPage(error=rejected)

        total = int(counted or 0)
        capped = total > COUNT_CAP
        page = SecretPage(
            total=min(total, COUNT_CAP) if capped else total, total_capped=capped
        )
        if not rows:
            return page

        names = await target_names(self.session, (row.target_id for row in rows))
        seen = await self._seen_before(scope, [row.fingerprint for row in rows])
        baseline = await self.session.scalar(select(secret_has_baseline(scope)))
        for row in rows:
            page.items.append(
                self._to_read(
                    row,
                    target_value=names.get(row.target_id),
                    is_new=bool(baseline) and row.fingerprint not in seen,
                )
            )
        return page

    def _to_read(
        self, row: Secret, *, target_value: str | None, is_new: bool
    ) -> SecretRead:
        spec = DETECTORS_BY_KEY.get(row.kind)
        return SecretRead(
            id=row.id,
            scan_id=row.scan_id,
            target_id=row.target_id,
            target_value=target_value,
            fingerprint=row.fingerprint,
            kind=row.kind,
            kind_label=spec.label if spec else row.kind,
            group=row.group,
            group_label=GROUP_LABELS.get(row.group, row.group),
            vendor=row.vendor,
            state=row.state,
            state_label=STATE_LABELS.get(row.state, row.state),
            is_secret=row.is_secret,
            value=row.value,
            subject=row.subject,
            meta=dict(row.meta or {}),
            host=row.host,
            url=row.url,
            http_asset_id=row.http_asset_id,
            source=row.source,
            source_label=SOURCE_LABELS.get(row.source, row.source),
            sightings=row.sightings,
            hosts=row.hosts,
            discovered_at=row.discovered_at,
            is_new=is_new,
        )

    async def _seen_before(
        self, scope: QueryScope, fingerprints: list[str]
    ) -> set[str]:
        if not fingerprints or not scope.ids:
            return set()
        rows = await self.session.execute(
            text(
                "SELECT DISTINCT e.fingerprint FROM secrets e "
                "JOIN secrets cur ON cur.scan_id = ANY(:sids) "
                "AND cur.fingerprint = e.fingerprint "
                "WHERE e.target_id = cur.target_id AND NOT (e.scan_id = ANY(:sids)) "
                "AND e.discovered_at < cur.discovered_at AND e.fingerprint = ANY(:fps)"
            ),
            {"sids": [str(i) for i in scope.ids], "fps": fingerprints},
        )
        return {row[0] for row in rows.all()}

    async def detail(self, scope: ScopeLike, secret_id: UUID) -> SecretDetail | None:
        scope = QueryScope.of(scope)
        row = await self.session.scalar(
            self._scoped(scope).where(Secret.id == secret_id)
        )
        if row is None:
            return None
        names = await target_names(self.session, [row.target_id])
        base = self._to_read(row, target_value=names.get(row.target_id), is_new=False)
        sightings = (
            (
                await self.session.execute(
                    select(SecretSighting)
                    .where(SecretSighting.secret_id == secret_id)
                    .order_by(SecretSighting.host, SecretSighting.url)
                    .limit(MAX_SIGHTINGS_SHOWN + 1)
                )
            )
            .scalars()
            .all()
        )
        truncated = len(sightings) > MAX_SIGHTINGS_SHOWN
        return SecretDetail(
            **base.model_dump(),
            context=row.context,
            sightings_truncated=truncated,
            sightings_shown=[
                SecretSightingRead(
                    id=s.id,
                    host=s.host,
                    url=s.url,
                    http_asset_id=s.http_asset_id,
                    source=s.source,
                    source_label=SOURCE_LABELS.get(s.source, s.source),
                    offset=s.offset,
                    context=s.context,
                )
                for s in sightings[:MAX_SIGHTINGS_SHOWN]
            ],
        )

    async def groups(self, scope: ScopeLike, f: SecretFilter, key: str) -> QueryGroups:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Secret.id).where(scope.match(Secret.scan_id))
        try:
            predicate = compile_secret_query(
                parse_query(f.q, SECRET_QUERY), self._context(scope, now)
            )
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        try:
            return await build_secret_groups(self.session, base, key)
        except DBAPIError as exc:
            await self.session.rollback()
            logger.info("secret groups failed", error=str(exc.orig))
            return QueryGroups(dimension=key)

    async def facets(self, scope: ScopeLike) -> SecretFacets:
        scope = QueryScope.of(scope)

        async def build() -> SecretFacets:
            return SecretFacets(
                state=await self._facet(scope, Secret.state, STATE_LABELS, STATE_ORDER),
                group=await self._facet(scope, Secret.group, GROUP_LABELS, GROUP_ORDER),
                kind=await self._kind_facet(scope),
                vendor=await self._facet(scope, Secret.vendor, {}, ()),
                source=await self._facet(scope, Secret.source, SOURCE_LABELS, ()),
                subject=await self._facet(scope, Secret.subject, {}, ()),
            )

        return await lead_cache.cached(
            self.session,
            name="secrets:facets",
            scans=scope.ids,
            facets="",
            model=SecretFacets,
            build=build,
        )

    async def _facet(
        self, scope: QueryScope, column, labels: dict[str, str], order: tuple[str, ...]
    ) -> list[SecretFacet]:
        rows = await self.session.execute(
            select(column, func.count())
            .where(scope.match(Secret.scan_id))
            .group_by(column)
            .order_by(func.count().desc())
            .limit(_FACET_LIMIT)
        )
        found = [
            SecretFacet(key=key, label=labels.get(key, key), count=count)
            for key, count in rows.all()
            if key
        ]
        if not order:
            return found
        rank = {key: index for index, key in enumerate(order)}
        return sorted(found, key=lambda item: rank.get(item.key, len(rank)))

    async def _kind_facet(self, scope: QueryScope) -> list[SecretFacet]:
        rows = await self.session.execute(
            select(Secret.kind, func.count())
            .where(scope.match(Secret.scan_id))
            .group_by(Secret.kind)
            .order_by(func.count().desc())
            .limit(_FACET_LIMIT)
        )
        return [
            SecretFacet(
                key=kind,
                label=DETECTORS_BY_KEY[kind].label
                if kind in DETECTORS_BY_KEY
                else kind,
                count=count,
            )
            for kind, count in rows.all()
            if kind
        ]

    async def coverage(self, scope: ScopeLike) -> SecretCoverageRead:
        scope = QueryScope.of(scope)

        async def build() -> SecretCoverageRead:
            rows = (
                (
                    await self.session.execute(
                        select(SecretCoverage).where(
                            scope.match(SecretCoverage.scan_id)
                        )
                    )
                )
                .scalars()
                .all()
            )
            exposed = int(
                await self.session.scalar(
                    select(func.count()).where(
                        scope.match(Secret.scan_id), Secret.is_secret.is_(True)
                    )
                )
                or 0
            )
            secrets = int(
                await self.session.scalar(
                    select(func.count()).where(scope.match(Secret.scan_id))
                )
                or 0
            )
            out = SecretCoverageRead(ran=bool(rows), secrets=secrets, exposed=exposed)
            scans: set[uuid.UUID] = set()
            for row in rows:
                scans.add(row.scan_id)
                out.documents_total += row.documents_total
                out.documents_read += row.documents_read
                out.bytes_read += row.bytes_read
                out.truncated += row.truncated
                out.detectors = max(out.detectors, row.detectors)
                if row.status in (
                    CoverageStatus.PARTIAL.value,
                    CoverageStatus.FAILED.value,
                ):
                    out.partial = True
                out.rows.append(
                    SecretCoverageRow(
                        source=row.source,
                        source_label=MINER_SOURCE_LABELS.get(row.source, row.source),
                        status=row.status,
                        documents_total=row.documents_total,
                        documents_read=row.documents_read,
                        bytes_read=row.bytes_read,
                        truncated=row.truncated,
                        skipped=row.skipped,
                        detectors=row.detectors,
                        matches=row.matches,
                        secrets=row.secrets,
                        dropped=dict(row.dropped or {}),
                        error=row.error,
                    )
                )
            out.scans = len(scans)
            out.rows.sort(key=lambda r: r.source)
            return out

        return await lead_cache.cached(
            self.session,
            name="secrets:coverage",
            scans=scope.ids,
            facets="",
            model=SecretCoverageRead,
            build=build,
        )

    async def counts(self, scope: ScopeLike, queries: list[str]) -> dict[str, int]:
        scope = QueryScope.of(scope)
        now = utc_now()
        out: dict[str, int] = {}
        for query in queries:
            base = self._scoped(scope)
            try:
                predicate = compile_secret_query(
                    parse_query(query, SECRET_QUERY), self._context(scope, now)
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
                select(func.count()).where(Secret.scan_id == scan_id)
            )
            or 0
        )
