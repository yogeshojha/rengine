from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, cast, desc, exists, func, select, text
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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
from app.services.endpoint_tree import (
    anomaly_for,
    archive_only_for,
    build_tree,
    static_clause,
)
from shared.definitions.asset_query import COUNT_CAP, ENDPOINT_QUERY
from shared.definitions.endpoints import (
    ADMIN_INTERESTS,
    CLASS_LABELS,
    COVERAGE_SOURCE_LABELS,
    INTEREST_LABELS,
    MAX_TREE_ROWS,
    SENSITIVE_INTERESTS,
    SOURCE_HELP,
    SOURCE_KIND,
    SOURCE_LABELS,
    STATIC_CLASSES,
    EndpointClass,
    PathInterest,
    folder_glyph,
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
    GonePage,
    HostPage,
    MergedLeaf,
    MergedLeafPage,
    SourceEvidence,
    TreeNode,
    VerifyBranchRequest,
    VerifyBranchResponse,
)
from shared.models.scan import Scan
from shared.services.celery_dispatch import dispatch_endpoint_verify
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_MERGED_HOST_SAMPLE = 12
_TOP_FOLDERS = 3
_HOST_PAGE_MAX = 200
_AUTH_WALL = (401, 403)
_STATUS_CLASSES = ("2xx", "3xx", "4xx", "5xx", "none")


def _is_static():
    return static_clause()


def _gone_from(previous_scan_id: UUID, scan_id: UUID):
    """Rows of the previous scan whose signature this scan never recorded."""
    current = aliased(Endpoint)
    return (
        Endpoint.scan_id == previous_scan_id,
        ~exists(
            select(1).where(
                current.scan_id == scan_id, current.signature == Endpoint.signature
            )
        ),
    )


def _status_bucket(status: int | None) -> str:
    if status is None:
        return "none"
    for name in _STATUS_CLASSES[:4]:
        if int(name[0]) * 100 <= status < (int(name[0]) + 1) * 100:
            return name
    return "none"


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
        if f.hide_static:
            query = query.where(~_is_static())
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
        out.static_total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Endpoint)
                .join(scoped, Endpoint.id == scoped.c.id)
                .where(_is_static())
            )
            or 0
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
        previous, _at = await self._previous_scan(scan_id)
        return await build_tree(
            self.session,
            base,
            scan_id=scan_id,
            mode=mode,
            previous_scan_id=previous,
            hide_static=f.hide_static,
        )

    async def _previous_scan(
        self, scan_id: UUID
    ) -> tuple[UUID | None, datetime | None]:
        """The latest earlier scan of the same target that recorded endpoints."""
        target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
        cutoff = (
            select(func.min(Endpoint.discovered_at))
            .where(Endpoint.scan_id == scan_id)
            .scalar_subquery()
        )
        row = (
            await self.session.execute(
                select(Endpoint.scan_id, func.max(Endpoint.discovered_at).label("at"))
                .where(
                    Endpoint.target_id == target,
                    Endpoint.scan_id != scan_id,
                    Endpoint.discovered_at < cutoff,
                )
                .group_by(Endpoint.scan_id)
                .order_by(desc("at"))
                .limit(1)
            )
        ).first()
        return (row.scan_id, row.at) if row else (None, None)

    async def _gone_by_host(
        self,
        scan_id: UUID,
        previous_scan_id: UUID | None,
        hosts: list[str],
        hide_static: bool,
    ) -> dict[str, int]:
        if previous_scan_id is None or not hosts:
            return {}
        query = (
            select(Endpoint.host, func.count())
            .where(*_gone_from(previous_scan_id, scan_id), Endpoint.host.in_(hosts))
            .group_by(Endpoint.host)
        )
        if hide_static:
            query = query.where(~static_clause())
        rows = await self.session.execute(query)
        return {host: int(n) for host, n in rows.all()}

    async def hosts(self, scan_id: UUID, f: EndpointFilter) -> HostPage:
        """The hosts of the outline, rolled up in SQL so ten thousand of them page cheaply."""
        now = utc_now()
        base = select(Endpoint.id).where(Endpoint.scan_id == scan_id)
        base = self._apply_filter(base, f, scan_id)
        try:
            predicate = self._compiled(scan_id, f, now)
        except QuerySyntaxError as exc:
            return HostPage(
                error=QueryError(
                    message=exc.message, hint=exc.hint, start=exc.start, end=exc.end
                )
            )
        if predicate is not None:
            base = base.where(predicate)
        scoped = base.subquery()
        interest = cast(Endpoint.interest, JSONB)
        sensitive = func.bool_or(interest.has_any(array(sorted(SENSITIVE_INTERESTS))))
        admin = func.bool_or(
            interest.has_any(array(sorted(ADMIN_INTERESTS | {PathInterest.AUTH.value})))
        )
        top_segment = func.split_part(Endpoint.dir_path, "/", 2)
        agg = (
            select(
                Endpoint.host.label("host"),
                func.count().label("n"),
                func.count().filter(Endpoint.is_probed.is_(True)).label("verified"),
                func.count().filter(Endpoint.param_count > 0).label("params"),
                func.count().filter(Endpoint.dir_path == "/").label("direct"),
                func.count(func.distinct(top_segment))
                .filter(Endpoint.dir_path != "/")
                .label("folders"),
                *[
                    func.count()
                    .filter(endpoint_status_class(name))
                    .label(f"s{name[0]}")
                    for name in _STATUS_CLASSES[:4]
                ],
                func.count()
                .filter(Endpoint.endpoint_class == EndpointClass.API.value)
                .label("api"),
                func.count().filter(endpoint_is_new(scan_id)).label("fresh"),
                func.count()
                .filter(Endpoint.status_code.in_(_AUTH_WALL))
                .label("walled"),
                sensitive.label("sensitive"),
                admin.label("admin"),
                func.min(Endpoint.url).label("sample"),
            )
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .group_by(Endpoint.host)
        )
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        totals = (
            await self.session.execute(
                select(func.count(func.distinct(Endpoint.host)), func.count())
                .select_from(Endpoint)
                .join(scoped, Endpoint.id == scoped.c.id)
            )
        ).one()
        size = max(1, min(f.size, _HOST_PAGE_MAX))
        offset = max(0, (max(f.page, 1) - 1) * size)
        ordered = agg.order_by(*self._host_order(agg, f)).limit(size).offset(offset)
        rows = (await self.session.execute(ordered)).all()
        names = [r.host for r in rows]
        interests = await self._host_values(scoped, names, Endpoint.interest)
        sources = await self._host_values(scoped, names, Endpoint.sources)
        classes = await self._host_classes(scoped, names)
        folders = await self._host_top_folders(scoped, names)
        previous, _at = await self._previous_scan(scan_id)
        gone = await self._gone_by_host(scan_id, previous, names, f.hide_static)
        items = []
        for r in rows:
            n = int(r.n)
            verified = int(r.verified)
            mix = {
                name: int(getattr(r, f"s{name[0]}"))
                for name in _STATUS_CLASSES[:4]
                if int(getattr(r, f"s{name[0]}"))
            }
            if n - verified:
                mix["none"] = n - verified
            flags = set(interests.get(r.host, []))
            host_sources = set(sources.get(r.host, []))
            items.append(
                TreeNode(
                    key=f"{r.host}/",
                    name=r.host,
                    path="/",
                    host=r.host,
                    kind="host",
                    depth=0,
                    direct_count=int(r.direct),
                    subtree_count=n,
                    child_count=int(r.folders),
                    hosts=1,
                    status_mix=dict(sorted(mix.items())),
                    class_mix=classes.get(r.host, {}),
                    sources=sorted(sources.get(r.host, [])),
                    interest=sorted(flags),
                    has_params=int(r.params) > 0,
                    params=int(r.params),
                    verified=verified,
                    unprobed=n - verified,
                    new_count=int(r.fresh),
                    gone_count=gone.get(r.host, 0),
                    anomaly=anomaly_for(
                        int(r.walled), mix.get("2xx", 0), mix.get("5xx", 0), verified
                    ),
                    archive_only=archive_only_for(host_sources, mix),
                    glyph=folder_glyph(flags, int(r.api), n),
                    sample_url=r.sample,
                    query=_token("host", ":", r.host),
                    lazy=True,
                    folders=int(r.folders),
                    top_folders=folders.get(r.host, []),
                )
            )
        return HostPage(
            items=items,
            total=int(totals[0] or 0),
            total_endpoints=int(totals[1] or 0),
            page=max(f.page, 1),
            size=size,
        )

    @staticmethod
    def _host_order(agg, f: EndpointFilter):
        cols = agg.selected_columns
        desc_ = f.direction == "desc"
        if f.sort in ("host", "path", "url"):
            return [cols.host.desc() if desc_ else cols.host.asc()]
        if f.sort == "status":
            return [cols.verified.desc(), cols.n.desc(), cols.host.asc()]
        if f.sort == "params":
            return [cols.params.desc(), cols.n.desc(), cols.host.asc()]
        if f.sort == "relevance":
            return [
                cols.sensitive.desc().nulls_last(),
                cols.admin.desc().nulls_last(),
                cols.n.desc(),
                cols.host.asc(),
            ]
        return [cols.n.desc(), cols.host.asc()]

    async def _host_values(
        self, scoped, hosts: list[str], column
    ) -> dict[str, list[str]]:
        if not hosts:
            return {}
        value = func.jsonb_array_elements_text(cast(column, JSONB)).column_valued("v")
        rows = await self.session.execute(
            select(Endpoint.host, value)
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .where(Endpoint.host.in_(hosts))
            .group_by(Endpoint.host, value)
        )
        out: dict[str, list[str]] = {}
        for host, v in rows.all():
            out.setdefault(host, []).append(str(v))
        return out

    async def _host_classes(
        self, scoped, hosts: list[str]
    ) -> dict[str, dict[str, int]]:
        if not hosts:
            return {}
        rows = await self.session.execute(
            select(Endpoint.host, Endpoint.endpoint_class, func.count())
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .where(Endpoint.host.in_(hosts))
            .group_by(Endpoint.host, Endpoint.endpoint_class)
        )
        out: dict[str, dict[str, int]] = {}
        for host, klass, n in rows.all():
            out.setdefault(host, {})[klass] = int(n)
        return out

    async def _host_top_folders(self, scoped, hosts: list[str]) -> dict[str, list[str]]:
        if not hosts:
            return {}
        segment = func.split_part(Endpoint.dir_path, "/", 2).label("seg")
        rows = await self.session.execute(
            select(Endpoint.host, segment, func.count().label("n"))
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .where(Endpoint.host.in_(hosts), Endpoint.dir_path != "/")
            .group_by(Endpoint.host, segment)
            .order_by(Endpoint.host, desc("n"), segment)
        )
        out: dict[str, list[str]] = {}
        for host, seg, _n in rows.all():
            bucket = out.setdefault(host, [])
            if len(bucket) < _TOP_FOLDERS:
                bucket.append(str(seg))
        return out

    async def merged_leaves(self, scan_id: UUID, f: EndpointFilter) -> MergedLeafPage:
        """One row per path shape inside a folder, folded across every host that serves it."""
        now = utc_now()
        base = self._scoped(
            scan_id,
            f.model_copy(update={"subtree": False}),
            columns=(
                Endpoint.id,
                Endpoint.host,
                Endpoint.path,
                Endpoint.filename,
                Endpoint.url,
                Endpoint.params,
                Endpoint.param_count,
                Endpoint.endpoint_class,
                Endpoint.is_probed,
                Endpoint.status_code,
                Endpoint.interest,
                Endpoint.sources,
                endpoint_is_new(scan_id).label("is_new"),
            ),
        )
        try:
            predicate = self._compiled(scan_id, f, now)
        except QuerySyntaxError:
            return MergedLeafPage()
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        rows = (
            await self.session.execute(
                base.order_by(Endpoint.path, Endpoint.host).limit(MAX_TREE_ROWS + 1)
            )
        ).all()
        truncated = len(rows) > MAX_TREE_ROWS
        folded: dict[tuple, MergedLeaf] = {}
        hosts: dict[tuple, set[str]] = {}
        for r in rows[:MAX_TREE_ROWS]:
            params = list(r.params or [])
            key = (r.path, tuple(params))
            leaf = folded.get(key)
            if leaf is None:
                leaf = MergedLeaf(
                    key=f"{r.path}?{'&'.join(params)}" if params else r.path,
                    path=r.path,
                    name=r.filename or "/",
                    params=params,
                    param_count=int(r.param_count or 0),
                    endpoint_class=r.endpoint_class,
                    sample_id=r.id,
                    sample_url=r.url,
                    sample_status=r.status_code if r.is_probed else None,
                    query=_token("path", "=", r.path),
                )
                folded[key] = leaf
                hosts[key] = set()
            leaf.endpoints += 1
            if r.is_new:
                leaf.new_count += 1
            hosts[key].add(r.host)
            bucket = _status_bucket(r.status_code) if r.is_probed else "none"
            leaf.status_mix[bucket] = leaf.status_mix.get(bucket, 0) + 1
            if not r.is_probed:
                leaf.unprobed += 1
            leaf.interest = sorted({*leaf.interest, *(r.interest or [])})
            leaf.sources = sorted({*leaf.sources, *(r.sources or [])})
        items = list(folded.values())
        for key, leaf in folded.items():
            names = sorted(hosts[key])
            leaf.hosts = len(names)
            leaf.host_names = names[:_MERGED_HOST_SAMPLE]
        items.sort(
            key=lambda x: (
                0 if x.interest else 1,
                0 if x.param_count else 1,
                -x.hosts,
                x.path,
            )
        )
        return MergedLeafPage(items=items, total=len(items), truncated=truncated)

    async def gone(self, scan_id: UUID, f: EndpointFilter) -> GonePage:
        """Endpoints the previous scan of this target recorded and this scan never did."""
        previous, previous_at = await self._previous_scan(scan_id)
        if previous is None:
            return GonePage()
        now = utc_now()
        base = select(Endpoint).where(*_gone_from(previous, scan_id))
        base = self._apply_filter(base, f.model_copy(update={"new": False}), previous)
        try:
            predicate = self._compiled(previous, f, now)
        except QuerySyntaxError as exc:
            return GonePage(
                error=QueryError(
                    message=exc.message, hint=exc.hint, start=exc.start, end=exc.end
                )
            )
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        size = max(1, min(f.size, 200))
        offset = max(0, (max(f.page, 1) - 1) * size)
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
        total = int(counted or 0)
        capped = total > COUNT_CAP
        return GonePage(
            items=[self._to_read(row) for row in rows],
            total=min(total, COUNT_CAP) if capped else total,
            total_capped=capped,
            page=max(f.page, 1),
            size=size,
            previous_scan_id=previous,
            previous_scan_at=previous_at,
        )

    async def verify_branch(
        self, scan_id: UUID, body: VerifyBranchRequest
    ) -> VerifyBranchResponse:
        """Queue verification of the unchecked, non-static endpoints under one folder."""
        query = select(func.count()).where(
            Endpoint.scan_id == scan_id,
            Endpoint.host == body.host,
            Endpoint.is_probed.is_(False),
            Endpoint.endpoint_class.notin_(tuple(STATIC_CLASSES)),
        )
        if body.dir_path and body.dir_path != "/":
            prefix = (
                body.dir_path if body.dir_path.endswith("/") else f"{body.dir_path}/"
            )
            escaped = (
                prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            query = query.where(Endpoint.dir_path.like(f"{escaped}%", escape="\\"))
        unverified = int(await self.session.scalar(query) or 0)
        if not unverified:
            return VerifyBranchResponse(queued=0, unverified=0, accepted=False)
        queued = min(unverified, body.limit)
        accepted = dispatch_endpoint_verify(
            str(scan_id), body.host, body.dir_path, queued
        )
        return VerifyBranchResponse(
            queued=queued if accepted else 0, unverified=unverified, accepted=accepted
        )

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

    async def summary(self, scan_id: UUID, host: str | None = None) -> EndpointSummary:
        scope = [Endpoint.scan_id == scan_id]
        if host:
            scope.append(Endpoint.host == host)
        row = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                ).where(*scope)
            )
        ).one()
        total = int(row.total)
        out = EndpointSummary(total=total, hosts=int(row.hosts))
        if not total:
            return out
        previous, previous_at = await self._previous_scan(scan_id)
        out.previous_scan_id = previous
        out.previous_scan_at = previous_at
        if previous is not None:
            gone_scope = [*_gone_from(previous, scan_id)]
            if host:
                gone_scope.append(Endpoint.host == host)
            out.gone = int(
                await self.session.scalar(select(func.count()).where(*gone_scope)) or 0
            )
        out.new = int(
            await self.session.scalar(
                select(func.count()).where(*scope, endpoint_is_new(scan_id))
            )
            or 0
        )
        out.probed = int(
            await self.session.scalar(
                select(func.count()).where(*scope, Endpoint.is_probed.is_(True))
            )
            or 0
        )
        out.live = int(
            await self.session.scalar(
                select(func.count()).where(*scope, endpoint_status_class("2xx"))
            )
            or 0
        )
        out.with_params = int(
            await self.session.scalar(
                select(func.count()).where(*scope, Endpoint.param_count > 0)
            )
            or 0
        )
        out.interesting = int(
            await self.session.scalar(
                select(func.count()).where(
                    *scope,
                    func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0,
                )
            )
            or 0
        )
        by_class = await self.session.execute(
            select(Endpoint.endpoint_class, func.count())
            .where(*scope)
            .group_by(Endpoint.endpoint_class)
        )
        out.by_class = {k: int(v) for k, v in by_class.all()}
        source = func.jsonb_array_elements_text(
            cast(Endpoint.sources, JSONB)
        ).column_valued("v")
        by_source = await self.session.execute(
            select(source, func.count(func.distinct(Endpoint.id)))
            .select_from(Endpoint)
            .where(*scope)
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
