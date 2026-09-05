from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, cast, desc, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    EndpointQueryContext,
    QuerySyntaxError,
    build_endpoint_groups,
    build_leads,
    compile_endpoint_query,
    endpoint_is_new,
    endpoint_status_class,
    parse_query,
    query_error_for,
)
from app.services.endpoint_tree import build_tree
from shared.definitions.asset_query import COUNT_CAP, ENDPOINT_QUERY
from shared.definitions.endpoints import (
    CLASS_LABELS,
    COVERAGE_SOURCE_LABELS,
    INTEREST_LABELS,
    SOURCE_HELP,
    SOURCE_KIND,
    SOURCE_LABELS,
)
from shared.logging import get_logger
from shared.models.asset_query import QueryError, QueryGroups, QueryLeads
from shared.models.endpoint import (
    CoverageRead,
    Endpoint,
    EndpointCoverage,
    EndpointDetail,
    EndpointFacet,
    EndpointFacets,
    EndpointFilter,
    EndpointPage,
    EndpointRead,
    EndpointSummary,
    EndpointTree,
    SourceEvidence,
)
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_STATUS_CLASSES = ("2xx", "3xx", "4xx", "5xx", "none")
_ARRAY_FACETS = {
    "source": Endpoint.sources,
    "interest": Endpoint.interest,
    "param": Endpoint.params,
}


def _needs_quote(value: str) -> bool:
    return any(c in value for c in ' ()"[]:=><~') or not value


def _token(field: str, op: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = f'"{escaped}"' if _needs_quote(value) else value
    return f"{field}{op}{quoted}"


class EndpointService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _context(scan_id: UUID, now: datetime) -> EndpointQueryContext:
        return EndpointQueryContext(scan_id=scan_id, now=now)

    @staticmethod
    def _apply_filter(query, f: EndpointFilter, scan_id: UUID):
        if f.host:
            query = query.where(Endpoint.host == f.host)
        if f.dir_path:
            prefix = f.dir_path if f.dir_path.endswith("/") else f"{f.dir_path}/"
            if f.subtree:
                escaped = (
                    prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                )
                query = query.where(Endpoint.dir_path.like(f"{escaped}%", escape="\\"))
            else:
                query = query.where(Endpoint.dir_path == prefix)
        if f.endpoint_class:
            query = query.where(Endpoint.endpoint_class == f.endpoint_class)
        if f.source:
            query = query.where(
                func.jsonb_exists(cast(Endpoint.sources, JSONB), f.source)
            )
        if f.interest:
            query = query.where(
                func.jsonb_exists(cast(Endpoint.interest, JSONB), f.interest)
            )
        if f.status_class:
            query = query.where(endpoint_status_class(f.status_class))
        if f.probed is not None:
            query = query.where(Endpoint.is_probed.is_(f.probed))
        if f.new:
            query = query.where(endpoint_is_new(scan_id))
        return query

    @staticmethod
    def _order(query, f: EndpointFilter):
        if f.sort == "relevance":
            # lead with what is worth opening: flagged, then input surface, then answering
            return query.order_by(
                (func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0)
                .desc()
                .nulls_last(),
                (Endpoint.param_count > 0).desc(),
                Endpoint.is_probed.desc(),
                endpoint_status_class("2xx").desc(),
                Endpoint.depth.asc(),
                Endpoint.host.asc(),
                Endpoint.path.asc(),
            )
        column = {
            "path": Endpoint.path,
            "url": Endpoint.url,
            "host": Endpoint.host,
            "status": Endpoint.status_code,
            "length": Endpoint.content_length,
            "params": Endpoint.param_count,
            "depth": Endpoint.depth,
            "seen": Endpoint.discovered_at,
            "class": Endpoint.endpoint_class,
        }.get(f.sort, Endpoint.path)
        primary = column.desc() if f.direction == "desc" else column.asc()
        return query.order_by(
            primary.nulls_last(), Endpoint.host.asc(), Endpoint.path.asc()
        )

    def _scoped(self, scan_id: UUID, f: EndpointFilter, columns=None):
        base = select(Endpoint) if columns is None else select(*columns)
        base = base.where(Endpoint.scan_id == scan_id)
        return self._apply_filter(base, f, scan_id)

    def _compiled(self, scan_id: UUID, f: EndpointFilter, now: datetime):
        return compile_endpoint_query(
            parse_query(f.q, ENDPOINT_QUERY), self._context(scan_id, now)
        )

    async def search(self, scan_id: UUID, f: EndpointFilter) -> EndpointPage:
        now = utc_now()
        base = self._scoped(scan_id, f)
        try:
            predicate = self._compiled(scan_id, f, now)
        except QuerySyntaxError as exc:
            return EndpointPage(
                error=QueryError(
                    message=exc.message, hint=exc.hint, start=exc.start, end=exc.end
                )
            )
        if predicate is not None:
            base = base.where(predicate)

        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        size = max(1, min(f.size, 200))
        offset = max(0, (max(f.page, 1) - 1) * size)
        try:
            counted = await self.session.scalar(
                select(func.count()).select_from(base.limit(COUNT_CAP + 1).subquery())
            )
            rows = (
                (
                    await self.session.execute(
                        self._order(base, f).limit(size).offset(offset)
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
            logger.info("endpoint query rejected", error=str(exc.orig))
            return EndpointPage(error=rejected)

        total = int(counted or 0)
        capped = total > COUNT_CAP
        page = EndpointPage(
            total=min(total, COUNT_CAP) if capped else total,
            total_capped=capped,
            page=max(f.page, 1),
            size=size,
        )
        if not rows:
            return page
        fresh = await self._new_signatures(scan_id, [r.signature for r in rows])
        page.items = [self._to_read(row, is_new=row.signature in fresh) for row in rows]
        return page

    def _to_read(self, row: Endpoint, *, is_new: bool = False) -> EndpointRead:
        return EndpointRead(
            id=row.id,
            scan_id=row.scan_id,
            target_id=row.target_id,
            signature=row.signature,
            url=row.url,
            host=row.host,
            port=row.port,
            scheme=row.scheme,
            path=row.path,
            dir_path=row.dir_path,
            filename=row.filename,
            extension=row.extension,
            depth=row.depth,
            params=list(row.params or []),
            param_count=row.param_count,
            variants=row.variants,
            more_variants=row.more_variants,
            methods=list(row.methods or []),
            sources=list(row.sources or []),
            primary_source=row.primary_source,
            evidence=_evidence(row),
            found_on=row.found_on,
            is_probed=row.is_probed,
            status_code=row.status_code,
            content_type=row.content_type,
            content_length=row.content_length,
            title=row.title,
            words=row.words,
            lines=row.lines,
            response_time=row.response_time,
            redirect_location=row.redirect_location,
            tech=list(row.tech or []),
            endpoint_class=row.endpoint_class,
            interest=list(row.interest or []),
            http_asset_id=row.http_asset_id,
            subdomain_id=row.subdomain_id,
            archive_last_seen=row.archive_last_seen,
            discovered_at=row.discovered_at,
            is_new=is_new,
        )

    async def detail(self, scan_id: UUID, endpoint_id: UUID) -> EndpointDetail | None:
        row = await self.session.scalar(
            select(Endpoint).where(
                Endpoint.id == endpoint_id, Endpoint.scan_id == scan_id
            )
        )
        if row is None:
            return None
        fresh = await self._new_signatures(scan_id, [row.signature])
        siblings = await self.session.scalar(
            select(func.count())
            .select_from(Endpoint)
            .where(
                Endpoint.scan_id == scan_id,
                Endpoint.host == row.host,
                Endpoint.dir_path == row.dir_path,
                Endpoint.id != row.id,
            )
        )
        base = self._to_read(row, is_new=row.signature in fresh)
        return EndpointDetail(
            **base.model_dump(),
            param_samples=list(row.param_samples or []),
            discovery=dict(row.discovery or {}),
            content_hash=row.content_hash,
            siblings=int(siblings or 0),
        )

    async def _new_signatures(self, scan_id: UUID, signatures: list[str]) -> set[str]:
        if not signatures:
            return set()
        rows = await self.session.execute(
            select(Endpoint.signature).where(
                Endpoint.scan_id == scan_id,
                Endpoint.signature.in_(signatures),
                endpoint_is_new(scan_id),
            )
        )
        return set(rows.scalars().all())

    async def facets(self, scan_id: UUID, f: EndpointFilter) -> EndpointFacets:
        now = utc_now()
        base = select(Endpoint.id).where(Endpoint.scan_id == scan_id)
        base = self._apply_filter(base, f, scan_id)
        try:
            predicate = self._compiled(scan_id, f, now)
        except QuerySyntaxError:
            return EndpointFacets()
        if predicate is not None:
            base = base.where(predicate)
        scoped = base.subquery()

        out = EndpointFacets()
        out.total = int(
            await self.session.scalar(select(func.count()).select_from(scoped)) or 0
        )
        out.endpoint_class = await self._column_facet(
            scoped, Endpoint.endpoint_class, CLASS_LABELS
        )
        out.extension = await self._column_facet(scoped, Endpoint.extension, {})
        out.host = await self._column_facet(scoped, Endpoint.host, {})
        out.source = await self._array_facet(scoped, Endpoint.sources, SOURCE_LABELS)
        out.interest = await self._array_facet(
            scoped, Endpoint.interest, INTEREST_LABELS
        )
        out.status_class = await self._status_facet(scoped)
        return out

    async def _column_facet(self, scoped, column, labels) -> list[EndpointFacet]:
        rows = await self.session.execute(
            select(column, func.count().label("n"))
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .where(column.isnot(None), cast(column, Text) != "")
            .group_by(column)
            .order_by(desc("n"), column)
            .limit(_FACET_LIMIT)
        )
        return [
            EndpointFacet(
                value=str(value),
                label=labels.get(str(value)) or str(value),
                count=int(n),
            )
            for value, n in rows.all()
        ]

    async def _array_facet(self, scoped, column, labels) -> list[EndpointFacet]:
        value = func.jsonb_array_elements_text(cast(column, JSONB)).column_valued("v")
        rows = await self.session.execute(
            select(
                value.label("value"), func.count(func.distinct(Endpoint.id)).label("n")
            )
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .group_by(value)
            .order_by(desc("n"), value)
            .limit(_FACET_LIMIT)
        )
        return [
            EndpointFacet(
                value=str(raw), label=labels.get(str(raw)) or str(raw), count=int(n)
            )
            for raw, n in rows.all()
        ]

    async def _status_facet(self, scoped) -> list[EndpointFacet]:
        out: list[EndpointFacet] = []
        for name in _STATUS_CLASSES:
            n = await self.session.scalar(
                select(func.count())
                .select_from(Endpoint)
                .join(scoped, Endpoint.id == scoped.c.id)
                .where(endpoint_status_class(name))
            )
            if n:
                out.append(
                    EndpointFacet(
                        value=name,
                        label="Not checked" if name == "none" else name,
                        count=int(n),
                    )
                )
        return out

    async def leads(self, scan_id: UUID, f: EndpointFilter) -> QueryLeads:
        now = utc_now()
        base = select(Endpoint.id).where(Endpoint.scan_id == scan_id)
        base = self._apply_filter(base, f, scan_id)
        context = self._context(scan_id, now)

        def predicate_for(query: str):
            return compile_endpoint_query(parse_query(query, ENDPOINT_QUERY), context)

        return await build_leads(
            self.session,
            base,
            ENDPOINT_QUERY.examples,
            predicate_for,
            filtered=f.has_facets(),
        )

    async def groups(self, scan_id: UUID, f: EndpointFilter, key: str) -> QueryGroups:
        now = utc_now()
        base = select(Endpoint.id).where(Endpoint.scan_id == scan_id)
        base = self._apply_filter(base, f, scan_id)
        try:
            predicate = self._compiled(scan_id, f, now)
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        return await build_endpoint_groups(self.session, base, key)

    async def tree(self, scan_id: UUID, f: EndpointFilter, mode: str) -> EndpointTree:
        now = utc_now()
        base = select(Endpoint.id).where(Endpoint.scan_id == scan_id)
        base = self._apply_filter(base, f, scan_id)
        try:
            predicate = self._compiled(scan_id, f, now)
        except QuerySyntaxError as exc:
            return EndpointTree(
                mode=mode,
                error=QueryError(
                    message=exc.message, hint=exc.hint, start=exc.start, end=exc.end
                ),
            )
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        return await build_tree(self.session, base, mode=mode)

    async def coverage(self, scan_id: UUID) -> list[CoverageRead]:
        rows = (
            (
                await self.session.execute(
                    select(EndpointCoverage)
                    .where(EndpointCoverage.scan_id == scan_id)
                    .order_by(EndpointCoverage.started_at)
                )
            )
            .scalars()
            .all()
        )
        return [
            CoverageRead(
                id=row.id,
                source=row.source,
                label=COVERAGE_SOURCE_LABELS.get(row.source, row.source),
                tool=row.tool,
                status=row.status,
                hosts_total=row.hosts_total,
                hosts_scanned=row.hosts_scanned,
                hosts_dropped=list(row.hosts_dropped or []),
                urls_found=row.urls_found,
                urls_stored=row.urls_stored,
                urls_probed=row.urls_probed,
                pages_fetched=row.pages_fetched,
                depth_reached=row.depth_reached,
                errors=row.errors,
                capped=row.capped,
                cap_reason=row.cap_reason,
                error=row.error,
                started_at=row.started_at,
                ended_at=row.ended_at,
                duration_seconds=row.duration_seconds,
            )
            for row in rows
        ]

    async def summary(self, scan_id: UUID) -> EndpointSummary:
        row = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                ).where(Endpoint.scan_id == scan_id)
            )
        ).one()
        total = int(row.total)
        out = EndpointSummary(total=total, hosts=int(row.hosts))
        if not total:
            return out
        out.probed = int(
            await self.session.scalar(
                select(func.count()).where(
                    Endpoint.scan_id == scan_id, Endpoint.is_probed.is_(True)
                )
            )
            or 0
        )
        out.live = int(
            await self.session.scalar(
                select(func.count()).where(
                    Endpoint.scan_id == scan_id, endpoint_status_class("2xx")
                )
            )
            or 0
        )
        out.with_params = int(
            await self.session.scalar(
                select(func.count()).where(
                    Endpoint.scan_id == scan_id, Endpoint.param_count > 0
                )
            )
            or 0
        )
        out.interesting = int(
            await self.session.scalar(
                select(func.count()).where(
                    Endpoint.scan_id == scan_id,
                    func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0,
                )
            )
            or 0
        )
        by_class = await self.session.execute(
            select(Endpoint.endpoint_class, func.count())
            .where(Endpoint.scan_id == scan_id)
            .group_by(Endpoint.endpoint_class)
        )
        out.by_class = {k: int(v) for k, v in by_class.all()}
        source = func.jsonb_array_elements_text(
            cast(Endpoint.sources, JSONB)
        ).column_valued("v")
        by_source = await self.session.execute(
            select(source, func.count(func.distinct(Endpoint.id)))
            .select_from(Endpoint)
            .where(Endpoint.scan_id == scan_id)
            .group_by(source)
        )
        out.by_source = {str(k): int(v) for k, v in by_source.all()}
        return out


def _evidence(row: Endpoint) -> list[SourceEvidence]:
    """Why each provider believes this endpoint exists, strongest source first."""
    discovery = dict(row.discovery or {})
    out: list[SourceEvidence] = []
    for source in row.sources or []:
        entry = discovery.get(source) or {}
        observed = entry.get("at")
        out.append(
            SourceEvidence(
                source=source,
                label=SOURCE_LABELS.get(source, source),
                kind=SOURCE_KIND.get(source, "derived"),
                detail=entry.get("detail") or SOURCE_HELP.get(source),
                found_on=entry.get("found_on"),
                observed_at=_parse(observed),
            )
        )
    return out


def _parse(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
