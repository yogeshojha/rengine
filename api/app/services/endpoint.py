from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Integer,
    Text,
    and_,
    cast,
    desc,
    exists,
    func,
    literal,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    EndpointQueryContext,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    build_endpoint_groups,
    build_leads,
    compile_endpoint_query,
    endpoint_is_new,
    endpoint_status_class,
    parse_query,
    query_error_for,
    vuln_suppressed,
)
from app.services.endpoint_tree import (
    anomaly_for,
    archive_only_for,
    build_tree,
    static_clause,
)
from app.services.target_names import target_names
from shared.definitions.asset_query import COUNT_CAP, ENDPOINT_QUERY
from shared.definitions.endpoints import (
    ADMIN_INTERESTS,
    ARCHIVE_SOURCES,
    CLASS_LABELS,
    COVERAGE_SOURCE_LABELS,
    INTEREST_LABELS,
    MAX_HOST_CHIPS,
    MAX_HOST_PARAMS,
    MAX_TREE_ROWS,
    PARAM_INTEREST_ORDER,
    ROOT_NOISE_DIRS,
    ROOT_NOISE_FILES,
    SENSITIVE_INTERESTS,
    SOURCE_HELP,
    SOURCE_KIND,
    SOURCE_LABELS,
    STATIC_CLASSES,
    EndpointClass,
    PathInterest,
    folder_glyph,
    param_interest,
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
    FolderChip,
    GonePage,
    HostBrief,
    HostIdentity,
    HostPage,
    MergedLeaf,
    MergedLeafPage,
    ParamStat,
    SourceEvidence,
    TreeNode,
    VerifyBranchRequest,
    VerifyBranchResponse,
)
from shared.models.http_asset import HttpAsset
from shared.models.scan import Scan
from shared.models.vulnerability import Vulnerability
from shared.services.celery_dispatch import dispatch_endpoint_verify
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_MERGED_HOST_SAMPLE = 12
_HOST_PAGE_MAX = 200
_HTTP_OK = 200
_W_SENSITIVE = 4.0
_W_CONTROL = 2.0
_W_AUTH = 1.5
_W_API = 1.5
_W_SIZE = 0.5
_AUTH_WALL = (401, 403)
_STATUS_CLASSES = ("2xx", "3xx", "4xx", "5xx", "none")


def _is_static():
    return static_clause()


def _root_noise():
    """The rows every parked hostname has: its root, robots, favicon and .well-known."""
    return or_(
        and_(
            Endpoint.dir_path == "/",
            func.coalesce(Endpoint.filename, "").in_(tuple(sorted(ROOT_NOISE_FILES))),
        ),
        *[Endpoint.dir_path.like(f"{d}%") for d in ROOT_NOISE_DIRS],
    )


def _archive_only_sources():
    return cast(Endpoint.sources, JSONB).contained_by(
        cast(literal(json.dumps(sorted(ARCHIVE_SOURCES))), JSONB)
    )


def _narrowed(f: EndpointFilter) -> bool:
    """Whether anything but the static switch constrains the rows."""
    return bool(
        f.q
        or f.dir_path
        or f.endpoint_class
        or f.source
        or f.interest
        or f.status_class
        or f.probed is not None
        or f.new
    )


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
    def _context(scope: QueryScope, now: datetime) -> EndpointQueryContext:
        return EndpointQueryContext(scope=scope, now=now)

    @staticmethod
    def _apply_filter(query, f: EndpointFilter, scope: QueryScope):
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
            query = query.where(endpoint_is_new(scope))
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

    def _scoped(self, scope: QueryScope, f: EndpointFilter, columns=None):
        base = select(Endpoint) if columns is None else select(*columns)
        base = base.where(scope.match(Endpoint.scan_id))
        return self._apply_filter(base, f, scope)

    def _compiled(self, scope: QueryScope, f: EndpointFilter, now: datetime):
        return compile_endpoint_query(
            parse_query(f.q, ENDPOINT_QUERY), self._context(scope, now)
        )

    async def search(self, scope: ScopeLike, f: EndpointFilter) -> EndpointPage:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope, f)
        try:
            predicate = self._compiled(scope, f, now)
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
        fresh = await self._new_signatures(scope, [r.signature for r in rows])
        names = await target_names(self.session, (r.target_id for r in rows))
        page.items = [
            self._to_read(
                row,
                is_new=row.signature in fresh,
                target_value=names.get(row.target_id),
            )
            for row in rows
        ]
        return page

    def _to_read(
        self, row: Endpoint, *, is_new: bool = False, target_value: str | None = None
    ) -> EndpointRead:
        return EndpointRead(
            id=row.id,
            scan_id=row.scan_id,
            target_id=row.target_id,
            target_value=target_value,
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

    async def detail(
        self, scope: ScopeLike, endpoint_id: UUID
    ) -> EndpointDetail | None:
        scope = QueryScope.of(scope)
        row = await self.session.scalar(
            select(Endpoint).where(
                Endpoint.id == endpoint_id, scope.match(Endpoint.scan_id)
            )
        )
        if row is None:
            return None
        fresh = await self._new_signatures(scope, [row.signature])
        siblings = await self.session.scalar(
            select(func.count())
            .select_from(Endpoint)
            .where(
                scope.match(Endpoint.scan_id),
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

    async def _new_signatures(
        self, scope: QueryScope, signatures: list[str]
    ) -> set[str]:
        if not signatures:
            return set()
        rows = await self.session.execute(
            select(Endpoint.signature).where(
                scope.match(Endpoint.scan_id),
                Endpoint.signature.in_(signatures),
                endpoint_is_new(scope),
            )
        )
        return set(rows.scalars().all())

    async def facets(self, scope: ScopeLike, f: EndpointFilter) -> EndpointFacets:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
        base = self._apply_filter(base, f, scope)
        try:
            predicate = self._compiled(scope, f, now)
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

    async def leads(self, scope: ScopeLike, f: EndpointFilter) -> QueryLeads:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
        base = self._apply_filter(base, f, scope)
        context = self._context(scope, now)

        def predicate_for(query: str):
            return compile_endpoint_query(parse_query(query, ENDPOINT_QUERY), context)

        return await build_leads(
            self.session,
            base,
            ENDPOINT_QUERY.examples,
            predicate_for,
            filtered=f.has_facets(),
        )

    async def groups(
        self, scope: ScopeLike, f: EndpointFilter, key: str
    ) -> QueryGroups:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
        base = self._apply_filter(base, f, scope)
        try:
            predicate = self._compiled(scope, f, now)
        except QuerySyntaxError:
            return QueryGroups(dimension=key)
        if predicate is not None:
            base = base.where(predicate)
        return await build_endpoint_groups(self.session, base, key)

    async def tree(
        self, scope: ScopeLike, f: EndpointFilter, mode: str
    ) -> EndpointTree:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
        base = self._apply_filter(base, f, scope)
        try:
            predicate = self._compiled(scope, f, now)
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
        previous, _at = await self._previous_scan(scope)
        return await build_tree(
            self.session,
            base,
            scope=scope,
            mode=mode,
            previous_scan_id=previous,
            hide_static=f.hide_static,
        )

    async def _previous_scan(
        self, scope: QueryScope
    ) -> tuple[UUID | None, datetime | None]:
        """The latest earlier scan of the same target that recorded endpoints."""
        single = scope.single
        if single is None:
            return None, None
        target = select(Scan.target_id).where(Scan.id == single).scalar_subquery()
        cutoff = (
            select(func.min(Endpoint.discovered_at))
            .where(Endpoint.scan_id == single)
            .scalar_subquery()
        )
        row = (
            await self.session.execute(
                select(Endpoint.scan_id, func.max(Endpoint.discovered_at).label("at"))
                .where(
                    Endpoint.target_id == target,
                    Endpoint.scan_id != single,
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
        scope: QueryScope,
        previous_scan_id: UUID | None,
        hosts: list[str],
        hide_static: bool,
    ) -> dict[str, int]:
        if previous_scan_id is None or not hosts or scope.single is None:
            return {}
        query = (
            select(Endpoint.host, func.count())
            .where(
                *_gone_from(previous_scan_id, scope.single), Endpoint.host.in_(hosts)
            )
            .group_by(Endpoint.host)
        )
        if hide_static:
            query = query.where(~static_clause())
        rows = await self.session.execute(query)
        return {host: int(n) for host, n in rows.all()}

    async def hosts(self, scope: ScopeLike, f: EndpointFilter) -> HostPage:
        """The estate as a ranked table: one row per host, rolled up in SQL so ten thousand page cheaply."""
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
        base = self._apply_filter(base, f, scope)
        try:
            predicate = self._compiled(scope, f, now)
        except QuerySyntaxError as exc:
            return HostPage(
                error=QueryError(
                    message=exc.message, hint=exc.hint, start=exc.start, end=exc.end
                )
            )
        if predicate is not None:
            base = base.where(predicate)
        scoped = base.subquery()
        agg, substantive = self._host_aggregate(scoped, scope)
        if f.hide_root_only:
            agg = agg.having(substantive > 0)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        totals = (
            await self.session.execute(
                select(func.count(func.distinct(Endpoint.host)), func.count())
                .select_from(Endpoint)
                .join(scoped, Endpoint.id == scoped.c.id)
            )
        ).one()
        root_only = 0
        if f.hide_root_only:
            parked = (
                select(Endpoint.host)
                .select_from(Endpoint)
                .join(scoped, Endpoint.id == scoped.c.id)
                .group_by(Endpoint.host)
                .having(substantive == 0)
                .subquery()
            )
            root_only = int(
                await self.session.scalar(select(func.count()).select_from(parked)) or 0
            )
        size = max(1, min(f.size, _HOST_PAGE_MAX))
        offset = max(0, (max(f.page, 1) - 1) * size)
        ordered = agg.order_by(*self._host_order(agg, f)).limit(size).offset(offset)
        rows = (await self.session.execute(ordered)).all()
        names = [r.host for r in rows]
        interests = await self._host_values(scoped, names, Endpoint.interest)
        sources = await self._host_values(scoped, names, Endpoint.sources)
        classes = await self._host_classes(scoped, names)
        chips = await self._host_chips(scoped, names)
        identity = await self._host_identity(scope, names)
        unfiltered = (
            await self._host_unfiltered(scope, names, f.hide_static)
            if _narrowed(f)
            else {}
        )
        previous, _at = await self._previous_scan(scope)
        gone = await self._gone_by_host(scope, previous, names, f.hide_static)
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
            host_chips = chips.get(r.host, [])
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
                    top_folders=[c.name for c in host_chips if c.path != "/"],
                    chips=host_chips,
                    api=int(r.api),
                    walled=int(r.walled),
                    unfiltered_count=unfiltered.get(r.host, 0),
                    identity=identity.get(r.host),
                )
            )
        return HostPage(
            items=items,
            total=max(0, int(totals[0] or 0) - root_only),
            total_endpoints=int(totals[1] or 0),
            root_only=root_only,
            page=max(f.page, 1),
            size=size,
        )

    @staticmethod
    def _host_aggregate(scoped, scope: QueryScope):
        """The per-host rollup and the count that separates an application from a parked name."""
        interest = cast(Endpoint.interest, JSONB)
        sensitive = func.bool_or(interest.has_any(array(sorted(SENSITIVE_INTERESTS))))
        admin = func.bool_or(
            interest.has_any(array(sorted(ADMIN_INTERESTS | {PathInterest.AUTH.value})))
        )
        top_segment = func.split_part(Endpoint.dir_path, "/", 2)
        substantive = func.count().filter(~_root_noise())
        control = func.bool_or(interest.has_any(array(sorted(ADMIN_INTERESTS))))
        auth = func.bool_or(interest.has_any(array([PathInterest.AUTH.value])))
        api_count = func.count().filter(
            Endpoint.endpoint_class == EndpointClass.API.value
        )
        input_count = func.count().filter(Endpoint.param_count > 0)
        verified_count = func.count().filter(Endpoint.is_probed.is_(True))
        # what a tester would open first: an exposed file, then a control surface, then input and reach
        score = (
            func.coalesce(cast(sensitive, Integer), 0) * _W_SENSITIVE
            + func.coalesce(cast(control, Integer), 0) * _W_CONTROL
            + func.coalesce(cast(auth, Integer), 0) * _W_AUTH
            + cast(api_count > 0, Integer) * _W_API
            + func.log(input_count + 1)
            + func.log(verified_count + 1)
            + func.log(func.count() + 1) * _W_SIZE
        )
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
                func.count().filter(endpoint_is_new(scope)).label("fresh"),
                func.count()
                .filter(Endpoint.status_code.in_(_AUTH_WALL))
                .label("walled"),
                sensitive.label("sensitive"),
                admin.label("admin"),
                score.label("score"),
                func.min(Endpoint.url).label("sample"),
            )
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .group_by(Endpoint.host)
        )
        return agg, substantive

    @staticmethod
    def _host_order(agg, f: EndpointFilter):
        cols = agg.selected_columns
        if f.sort in ("host", "path", "url"):
            return [cols.host.desc() if f.direction == "desc" else cols.host.asc()]
        if f.sort == "relevance":
            return [cols.score.desc().nulls_last(), cols.n.desc(), cols.host.asc()]
        lead = {
            "status": cols.verified,
            "verified": cols.verified,
            "params": cols.params,
            "input": cols.params,
            "api": cols.api,
            "new": cols.fresh,
        }.get(f.sort, cols.n)
        return [lead.desc(), cols.n.desc(), cols.host.asc()]

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

    async def _host_chips(
        self, scoped, hosts: list[str]
    ) -> dict[str, list[FolderChip]]:
        """Every top-level folder of each host, ranked the way the outline ranks them."""
        if not hosts:
            return {}
        interest = cast(Endpoint.interest, JSONB)
        segment = func.split_part(Endpoint.dir_path, "/", 2).label("seg")
        rows = await self.session.execute(
            select(
                Endpoint.host,
                segment,
                func.count().label("n"),
                func.bool_or(
                    interest.has_any(array(sorted(SENSITIVE_INTERESTS)))
                ).label("sensitive"),
                func.bool_or(interest.has_any(array(sorted(ADMIN_INTERESTS)))).label(
                    "admin"
                ),
                func.bool_or(interest.has_any(array([PathInterest.AUTH.value]))).label(
                    "auth"
                ),
                func.count()
                .filter(Endpoint.endpoint_class == EndpointClass.API.value)
                .label("api"),
                func.count()
                .filter(or_(endpoint_status_class("2xx"), endpoint_status_class("3xx")))
                .label("answering"),
                func.bool_and(_archive_only_sources()).label("archived"),
            )
            .select_from(Endpoint)
            .join(scoped, Endpoint.id == scoped.c.id)
            .where(
                Endpoint.host.in_(hosts),
                *[~Endpoint.dir_path.like(f"{d}%") for d in ROOT_NOISE_DIRS],
            )
            .group_by(Endpoint.host, segment)
        )
        grouped: dict[str, list[tuple]] = {}
        for r in rows.all():
            flags: set[str] = set()
            if r.sensitive:
                flags.add(PathInterest.VCS.value)
            if r.admin:
                flags.add(PathInterest.ADMIN.value)
            if r.auth:
                flags.add(PathInterest.AUTH.value)
            n = int(r.n)
            api = int(r.api)
            glyph = folder_glyph(flags, api, n)
            answering = int(r.answering)
            path = f"/{r.seg}/" if r.seg else "/"
            rank = (
                1 if path == "/" else 0,
                0 if r.sensitive else 1,
                0 if (r.admin or r.auth) else 1,
                0 if api else 1,
                0 if answering else 1,
                -n,
                path,
            )
            grouped.setdefault(r.host, []).append(
                (
                    rank,
                    FolderChip(
                        name=str(r.seg) if r.seg else "/",
                        path=path,
                        count=n,
                        glyph=glyph,
                        archive_only=bool(r.archived) and answering == 0,
                        query=_token("dir", ":" if r.seg else "=", path),
                    ),
                )
            )
        return {
            host: [chip for _rank, chip in sorted(items, key=lambda x: x[0])][
                :MAX_HOST_CHIPS
            ]
            for host, items in grouped.items()
        }

    async def _host_identity(
        self, scope: QueryScope, hosts: list[str]
    ) -> dict[str, HostIdentity]:
        """What each host's own HTTP asset says it is, preferring the answer that was a page."""
        if not hosts:
            return {}
        rows = await self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.status_code,
                HttpAsset.title,
                HttpAsset.tech,
                HttpAsset.id,
            )
            .where(scope.match(HttpAsset.scan_id), HttpAsset.host.in_(hosts))
            .distinct(HttpAsset.host)
            .order_by(
                HttpAsset.host,
                (HttpAsset.status_code == _HTTP_OK).desc().nulls_last(),
                HttpAsset.status_code.asc().nulls_last(),
            )
        )
        return {
            host: HostIdentity(
                status_code=status,
                title=title or None,
                tech=[str(t) for t in (tech or [])],
                http_asset_id=asset_id,
            )
            for host, status, title, tech, asset_id in rows.all()
        }

    async def _host_unfiltered(
        self, scope: QueryScope, hosts: list[str], hide_static: bool
    ) -> dict[str, int]:
        """How many endpoints each host holds before the query narrowed it."""
        if not hosts:
            return {}
        query = (
            select(Endpoint.host, func.count())
            .where(scope.match(Endpoint.scan_id), Endpoint.host.in_(hosts))
            .group_by(Endpoint.host)
        )
        if hide_static:
            query = query.where(~_is_static())
        return {host: int(n) for host, n in (await self.session.execute(query)).all()}

    async def pick(
        self, scope: ScopeLike, f: EndpointFilter, limit: int
    ) -> list[Endpoint]:
        """The rows a filter names, in relevance order, capped: what a proxy is handed."""
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope, f)
        predicate = self._compiled(scope, f, now)
        if predicate is not None:
            base = base.where(predicate)
        base = self._order(base, EndpointFilter(sort="relevance"))
        return list((await self.session.execute(base.limit(limit))).scalars().all())

    async def host_brief(
        self, scope: ScopeLike, host: str, hide_static: bool = True
    ) -> HostBrief:
        """The sitemap header: what the host is, the facts that pivot, the parameter surface."""
        scope = QueryScope.of(scope)
        reach = [scope.match(Endpoint.scan_id), Endpoint.host == host]
        if hide_static:
            reach.append(~_is_static())

        async def count(*extra) -> int:
            return int(
                await self.session.scalar(select(func.count()).where(*reach, *extra))
                or 0
            )

        out = HostBrief(host=host, total=await count())
        out.identity = (await self._host_identity(scope, [host])).get(host)
        by_class = await self.session.execute(
            select(Endpoint.endpoint_class, func.count())
            .where(scope.match(Endpoint.scan_id), Endpoint.host == host)
            .group_by(Endpoint.endpoint_class)
        )
        out.by_class = {k: int(v) for k, v in by_class.all()}
        out.static_total = int(
            await self.session.scalar(
                select(func.count()).where(
                    scope.match(Endpoint.scan_id), Endpoint.host == host, _is_static()
                )
            )
            or 0
        )
        if not out.total:
            return out
        out.probed = await count(Endpoint.is_probed.is_(True))
        out.live = await count(endpoint_status_class("2xx"))
        out.with_params = await count(Endpoint.param_count > 0)
        out.api = await count(Endpoint.endpoint_class == EndpointClass.API.value)
        out.walled = await count(Endpoint.status_code.in_(_AUTH_WALL))
        out.interesting = await count(
            func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0
        )
        out.new = await count(endpoint_is_new(scope))
        previous, previous_at = await self._previous_scan(scope)
        out.previous_scan_at = previous_at
        if previous is not None:
            gone_scope = [*_gone_from(previous, scope.single), Endpoint.host == host]
            if hide_static:
                gone_scope.append(~_is_static())
            out.gone = int(
                await self.session.scalar(select(func.count()).where(*gone_scope)) or 0
            )
        out.findings = int(
            await self.session.scalar(
                select(func.count()).where(
                    scope.match(Vulnerability.scan_id),
                    Vulnerability.host == host,
                    ~vuln_suppressed(scope),
                )
            )
            or 0
        )
        name = func.jsonb_array_elements_text(
            cast(Endpoint.params, JSONB)
        ).column_valued("name")
        rows = (
            await self.session.execute(
                select(name, func.count().label("n"))
                .select_from(Endpoint)
                .where(*reach)
                .group_by(name)
            )
        ).all()
        stats = [
            ParamStat(name=str(n), count=int(c), interest=param_interest(str(n)))
            for n, c in rows
        ]
        out.params_total = len(stats)
        rank = {k: i for i, k in enumerate(PARAM_INTEREST_ORDER)}
        out.params = sorted(
            stats,
            key=lambda p: (rank.get(p.interest or "", len(rank)), -p.count, p.name),
        )[:MAX_HOST_PARAMS]
        return out

    async def merged_leaves(
        self, scope: ScopeLike, f: EndpointFilter
    ) -> MergedLeafPage:
        """One row per path shape inside a folder, folded across every host that serves it."""
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(
            scope,
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
                endpoint_is_new(scope).label("is_new"),
            ),
        )
        try:
            predicate = self._compiled(scope, f, now)
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

    async def gone(self, scope: ScopeLike, f: EndpointFilter) -> GonePage:
        """Endpoints the previous scan of this target recorded and this scan never did."""
        scope = QueryScope.of(scope)
        previous, previous_at = await self._previous_scan(scope)
        if previous is None or scope.single is None:
            return GonePage()
        now = utc_now()
        base = select(Endpoint).where(*_gone_from(previous, scope.single))
        base = self._apply_filter(
            base, f.model_copy(update={"new": False}), QueryScope.of(previous)
        )
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

    async def coverage(self, scope: ScopeLike) -> list[CoverageRead]:
        scope = QueryScope.of(scope)
        rows = (
            (
                await self.session.execute(
                    select(EndpointCoverage)
                    .where(scope.match(EndpointCoverage.scan_id))
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

    async def summary(
        self, scope: ScopeLike, host: str | None = None
    ) -> EndpointSummary:
        scope = QueryScope.of(scope)
        reach = [scope.match(Endpoint.scan_id)]
        if host:
            reach.append(Endpoint.host == host)
        row = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                ).where(*reach)
            )
        ).one()
        total = int(row.total)
        out = EndpointSummary(total=total, hosts=int(row.hosts))
        if not total:
            return out
        previous, previous_at = await self._previous_scan(scope)
        out.previous_scan_id = previous
        out.previous_scan_at = previous_at
        if previous is not None:
            gone_scope = [*_gone_from(previous, scope.single)]
            if host:
                gone_scope.append(Endpoint.host == host)
            out.gone = int(
                await self.session.scalar(select(func.count()).where(*gone_scope)) or 0
            )
        out.new = int(
            await self.session.scalar(
                select(func.count()).where(*reach, endpoint_is_new(scope))
            )
            or 0
        )
        out.probed = int(
            await self.session.scalar(
                select(func.count()).where(*reach, Endpoint.is_probed.is_(True))
            )
            or 0
        )
        out.live = int(
            await self.session.scalar(
                select(func.count()).where(*reach, endpoint_status_class("2xx"))
            )
            or 0
        )
        out.with_params = int(
            await self.session.scalar(
                select(func.count()).where(*reach, Endpoint.param_count > 0)
            )
            or 0
        )
        out.interesting = int(
            await self.session.scalar(
                select(func.count()).where(
                    *reach,
                    func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0,
                )
            )
            or 0
        )
        by_class = await self.session.execute(
            select(Endpoint.endpoint_class, func.count())
            .where(*reach)
            .group_by(Endpoint.endpoint_class)
        )
        out.by_class = {k: int(v) for k, v in by_class.all()}
        source = func.jsonb_array_elements_text(
            cast(Endpoint.sources, JSONB)
        ).column_valued("v")
        by_source = await self.session.execute(
            select(source, func.count(func.distinct(Endpoint.id)))
            .select_from(Endpoint)
            .where(*reach)
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
