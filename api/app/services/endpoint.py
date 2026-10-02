from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Integer,
    Text,
    and_,
    case,
    cast,
    desc,
    exists,
    func,
    literal,
    or_,
    select,
    text,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services import scan_deltas as stored_deltas
from app.services.endpoint_tree import (
    anomaly_for,
    archive_only_for,
    build_tree,
    status_bucket,
)
from app.services.target_names import target_names
from shared.definitions.asset_query import ALL_TAB, COUNT_CAP, ENDPOINT_QUERY
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
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.asset_query import QueryCounts, QueryGroups, QueryLeads
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
from shared.models.scan_context import PROBE_SCHEME
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    QueryScope,
    QuerySyntaxError,
    ScopeLike,
    build_endpoint_groups,
    build_leads,
    compile_endpoint_query,
    count_named,
    element_counts,
    endpoint_baseline,
    endpoint_is_new,
    endpoint_status_class,
    lead_cache,
    parse_query,
    query_error_for,
    syntax_error,
    vuln_suppressed,
)
from shared.services.asset_query import predicates as preds
from shared.services.asset_query.tokens import token as _token
from shared.services.celery_dispatch import dispatch_endpoint_verify
from shared.services.scope_filter import matches_any
from shared.services.surface_query import endpoints as surface_endpoints
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_FACET_LIMIT = 30
_MERGED_HOST_SAMPLE = 12
_HOST_PAGE_MAX = 200
_W_SENSITIVE = 4.0
_W_CONTROL = 2.0
_W_AUTH = 1.5
_W_API = 1.5
_W_SIZE = 0.5
_STATUS_CLASSES = ("2xx", "3xx", "4xx", "5xx", "none")
_STATUS_LABELS = {"none": "Not checked"}
_NEW_LEAD = _token("is", ":", "new")


def _label(rows: list[tuple[str, int]], labels: dict) -> list[EndpointFacet]:
    return [
        EndpointFacet(value=value, label=labels.get(value) or value, count=count)
        for value, count in rows
    ]


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


class _Reach:
    """The rows a query counts."""

    def __init__(self, scope: QueryScope, base, narrowed: bool):
        self.scope = scope
        self.source = Endpoint
        self.limit = base.whereclause if narrowed else scope.match(Endpoint.scan_id)

    def within(self, query):
        return query.select_from(self.source).where(self.limit)


def _column_branch(reach: _Reach, column):
    return (
        reach.within(select(cast(column, Text).label("value"), func.count().label("n")))
        .where(column.isnot(None), cast(column, Text) != "")
        .group_by(column)
        .order_by(desc("n"), cast(column, Text))
        .limit(_FACET_LIMIT)
        .subquery()
    )


def _array_branch(reach: _Reach, column):
    counted = element_counts(reach.within(select(Endpoint.id)), column).subquery()
    return (
        select(counted.c.value, counted.c.n)
        .order_by(desc(counted.c.n), counted.c.value)
        .limit(_FACET_LIMIT)
        .subquery()
    )


def _status_branch(reach: _Reach):
    bucket = case(
        *[(endpoint_status_class(name), literal(name)) for name in _STATUS_CLASSES],
        else_=None,
    )
    return (
        reach.within(select(bucket.label("value"), func.count().label("n")))
        .where(bucket.isnot(None))
        .group_by(bucket)
        .subquery()
    )


class EndpointService:
    def __init__(self, session: AsyncSession):
        self.session = session

    _context = staticmethod(surface_endpoints.context)
    _apply_filter = staticmethod(surface_endpoints.apply_filter)
    _order = staticmethod(surface_endpoints.order)
    _scoped = staticmethod(surface_endpoints.scoped)
    _compiled = staticmethod(surface_endpoints.compiled)

    async def seeds(
        self, scope: ScopeLike, f: EndpointFilter, limit: int
    ) -> list[tuple[str, UUID]]:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope, f, columns=(Endpoint.host, Endpoint.scan_id))
        try:
            predicate = self._compiled(scope, f, now)
        except QuerySyntaxError:
            return []
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        rows = await self.session.execute(
            base.distinct().order_by(Endpoint.host).limit(limit)
        )
        return [(host, scan_id) for host, scan_id in rows.all()]

    async def search(self, scope: ScopeLike, f: EndpointFilter) -> EndpointPage:
        scope = QueryScope.of(scope)
        now = utc_now()
        base = self._scoped(scope, f)
        try:
            predicate = self._compiled(scope, f, now)
        except QuerySyntaxError as exc:
            return EndpointPage(error=syntax_error(exc))
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
        reach = _Reach(scope, base, f.has_facets() or predicate is not None)

        counts = (
            await self.session.execute(
                reach.within(
                    select(
                        func.count().label("total"),
                        func.count()
                        .filter(surface_endpoints.static_clause())
                        .label("static"),
                    )
                )
            )
        ).one()

        out = EndpointFacets()
        out.total = int(counts.total or 0)
        out.static_total = int(counts.static or 0)

        grouped = await self._facets(
            [
                ("endpoint_class", _column_branch(reach, Endpoint.endpoint_class)),
                ("extension", _column_branch(reach, Endpoint.extension)),
                ("host", _column_branch(reach, Endpoint.host)),
                ("status_class", _status_branch(reach)),
            ]
        )
        arrays = await self._facets(
            [
                ("source", _array_branch(reach, Endpoint.sources)),
                ("interest", _array_branch(reach, Endpoint.interest)),
            ]
        )
        out.endpoint_class = _label(grouped["endpoint_class"], CLASS_LABELS)
        out.extension = _label(grouped["extension"], {})
        out.host = _label(grouped["host"], {})
        out.status_class = _label(
            sorted(grouped["status_class"], key=lambda r: _STATUS_CLASSES.index(r[0])),
            _STATUS_LABELS,
        )
        out.source = _label(arrays["source"], SOURCE_LABELS)
        out.interest = _label(arrays["interest"], INTEREST_LABELS)
        return out

    async def _facets(self, branches) -> dict[str, list[tuple[str, int]]]:
        """One statement for many facets."""
        rows = await self.session.execute(
            union_all(
                *[
                    select(
                        literal(kind).label("kind"),
                        branch.c.value.label("value"),
                        branch.c.n.label("n"),
                    )
                    for kind, branch in branches
                ]
            )
        )
        out: dict[str, list[tuple[str, int]]] = {kind: [] for kind, _ in branches}
        for kind, value, n in rows.all():
            out[kind].append((str(value), int(n)))
        for values in out.values():
            values.sort(key=lambda pair: (-pair[1], pair[0]))
        return out

    async def tabs(self, scope: ScopeLike, f: EndpointFilter) -> QueryCounts:
        """Rows under each class tab, for the filter without its own class."""
        scope = QueryScope.of(scope)
        f = f.model_copy(update={"endpoint_class": None})

        async def _build() -> QueryCounts:
            now = utc_now()
            base = self._scoped(scope, f, columns=(Endpoint.id,))
            try:
                predicate = self._compiled(scope, f, now)
            except QuerySyntaxError:
                return QueryCounts()
            if predicate is not None:
                base = base.where(predicate)
            await self.session.execute(text(STATEMENT_TIMEOUT))
            await self.session.execute(text(NO_JIT))
            tabs = {k.value: Endpoint.endpoint_class == k.value for k in EndpointClass}
            try:
                return await count_named(self.session, base, {ALL_TAB: None, **tabs})
            except DBAPIError as exc:
                await self.session.rollback()
                logger.info("endpoint tabs failed", error=str(exc.orig))
                return QueryCounts()

        return await lead_cache.cached(
            self.session,
            name="tabs:endpoints",
            scans=scope.ids,
            facets=lead_cache.filter_of(f),
            model=QueryCounts,
            build=_build,
            keep=lambda counted: counted.computed,
            ttl=lead_cache.SEARCH_TTL_SECONDS,
            live_ttl=None,
        )

    async def leads(self, scope: ScopeLike, f: EndpointFilter) -> QueryLeads:
        scope = QueryScope.of(scope)

        async def _build() -> QueryLeads:
            now = utc_now()
            base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
            base = self._apply_filter(base, f, scope)
            context = self._context(scope, now)

            def predicate_for(query: str):
                return compile_endpoint_query(
                    parse_query(query, ENDPOINT_QUERY), context
                )

            fresh = None
            if not (f.has_facets() or f.ids):
                fresh = await self._stored_new(scope)
            return await build_leads(
                self.session,
                base,
                ENDPOINT_QUERY.examples,
                predicate_for,
                filtered=f.has_facets(),
                known=None if fresh is None else {_NEW_LEAD: fresh},
            )

        return await lead_cache.leads(
            self.session,
            dimension="endpoints",
            scans=scope.ids,
            facets=lead_cache.facets_of(f),
            build=_build,
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
                error=syntax_error(exc),
            )
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        previous, _at = await self._previous_scan(scope)
        return await build_tree(
            self.session,
            base,
            scope=scope,
            mode=mode,
            previous_scan_id=previous,
            hide_static=f.hide_static,
        )

    async def _stored_new(self, scope: QueryScope) -> int | None:
        """`is:new` over every row of settled scans, from the stored first-seen counts."""
        if not scope.ids:
            return None
        statuses = (
            await self.session.execute(
                select(Scan.id, Scan.status).where(Scan.id.in_(scope.ids))
            )
        ).all()
        if len(statuses) != len(set(scope.ids)) or any(
            status not in SCAN_TERMINAL_STATUSES for _, status in statuses
        ):
            return None
        held = (
            await self.session.execute(
                select(*[endpoint_baseline(scan_id) for scan_id in scope.ids])
            )
        ).one()
        counted = [scan_id for scan_id, has in zip(scope.ids, held, strict=True) if has]
        if not counted:
            return 0
        firsts = await stored_deltas.first_seen(
            self.session, SurfaceDimension.ENDPOINTS.value, counted
        )
        return sum(firsts.get(scan_id, 0) for scan_id in counted)

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
                select(Endpoint.scan_id, Endpoint.discovered_at.label("at"))
                .where(
                    Endpoint.target_id == target,
                    Endpoint.scan_id != single,
                    Endpoint.discovered_at < cutoff,
                )
                .order_by(Endpoint.discovered_at.desc())
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
            query = query.where(~surface_endpoints.static_clause())
        rows = await self.session.execute(query)
        return {host: int(n) for host, n in rows.all()}

    async def hosts(self, scope: ScopeLike, f: EndpointFilter) -> HostPage:
        """One row per host, ranked."""
        scope = QueryScope.of(scope)
        now = utc_now()
        base = select(Endpoint.id).where(scope.match(Endpoint.scan_id))
        base = self._apply_filter(base, f, scope)
        try:
            predicate = self._compiled(scope, f, now)
        except QuerySyntaxError as exc:
            return HostPage(error=syntax_error(exc))
        if predicate is not None:
            base = base.where(predicate)
        reach = _Reach(scope, base, f.has_facets() or predicate is not None)
        agg, substantive = self._host_aggregate(reach)
        if f.hide_root_only:
            agg = agg.having(substantive > 0)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        per_host = (
            select(
                Endpoint.host,
                func.count().label("n"),
                substantive.label("substantive"),
            )
            .select_from(reach.source)
            .where(reach.limit)
            .group_by(Endpoint.host)
            .subquery()
        )
        totals = (
            await self.session.execute(
                select(
                    func.count(per_host.c.host),
                    func.sum(per_host.c.n),
                    func.count().filter(per_host.c.substantive == 0),
                )
            )
        ).one()
        root_only = int(totals[2] or 0) if f.hide_root_only else 0
        fresh = (
            select(Endpoint.host.label("host"), func.count().label("n"))
            .select_from(reach.source)
            .where(reach.limit, endpoint_is_new(scope))
            .group_by(Endpoint.host)
            .subquery("fresh")
        )
        rolled = agg.subquery("rolled")
        ranked = select(rolled, func.coalesce(fresh.c.n, 0).label("fresh")).select_from(
            rolled.outerjoin(fresh, fresh.c.host == rolled.c.host)
        )
        size = max(1, min(f.size, _HOST_PAGE_MAX))
        offset = max(0, (max(f.page, 1) - 1) * size)
        ordered = (
            ranked.order_by(*self._host_order(ranked, f)).limit(size).offset(offset)
        )
        rows = (await self.session.execute(ordered)).all()
        names = [r.host for r in rows]
        folders = await self._host_folders(reach, names)
        interests = await self._host_values(reach, names, Endpoint.interest)
        sources = await self._host_values(reach, names, Endpoint.sources)
        classes = await self._host_classes(reach, names)
        chips = await self._host_chips(reach, names)
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
                    child_count=folders.get(r.host, 0),
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
                    folders=folders.get(r.host, 0),
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
    def _host_aggregate(reach: _Reach):
        """The per-host rollup and the count that separates an application from a parked name."""
        interest = cast(Endpoint.interest, JSONB)
        sensitive = func.bool_or(interest.has_any(array(sorted(SENSITIVE_INTERESTS))))
        substantive = func.count().filter(~_root_noise())
        control = func.bool_or(interest.has_any(array(sorted(ADMIN_INTERESTS))))
        auth = func.bool_or(interest.has_any(array([PathInterest.AUTH.value])))
        api_count = func.count().filter(
            Endpoint.endpoint_class == EndpointClass.API.value
        )
        input_count = func.count().filter(Endpoint.param_count > 0)
        verified_count = func.count().filter(Endpoint.is_probed.is_(True))
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
                *[
                    func.count()
                    .filter(endpoint_status_class(name))
                    .label(f"s{name[0]}")
                    for name in _STATUS_CLASSES[:4]
                ],
                func.count()
                .filter(Endpoint.endpoint_class == EndpointClass.API.value)
                .label("api"),
                func.count()
                .filter(Endpoint.status_code.in_(preds.AUTH_STATUS))
                .label("walled"),
                score.label("score"),
                func.min(Endpoint.url).label("sample"),
            )
            .select_from(reach.source)
            .where(reach.limit)
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

    async def _host_folders(self, reach: _Reach, hosts: list[str]) -> dict[str, int]:
        if not hosts:
            return {}
        rows = await self.session.execute(
            select(
                Endpoint.host,
                func.count(func.distinct(func.split_part(Endpoint.dir_path, "/", 2))),
            )
            .select_from(reach.source)
            .where(reach.limit, Endpoint.host.in_(hosts), Endpoint.dir_path != "/")
            .group_by(Endpoint.host)
        )
        return {host: int(n) for host, n in rows.all()}

    async def _host_values(
        self, reach: _Reach, hosts: list[str], column
    ) -> dict[str, list[str]]:
        if not hosts:
            return {}
        counted = element_counts(
            reach.within(select(Endpoint.id)).where(Endpoint.host.in_(hosts)),
            column,
            Endpoint.host,
        ).subquery()
        rows = await self.session.execute(select(counted.c.host, counted.c.value))
        out: dict[str, list[str]] = {}
        for host, v in rows.all():
            out.setdefault(host, []).append(str(v))
        return out

    async def _host_classes(
        self, reach: _Reach, hosts: list[str]
    ) -> dict[str, dict[str, int]]:
        if not hosts:
            return {}
        rows = await self.session.execute(
            select(Endpoint.host, Endpoint.endpoint_class, func.count())
            .select_from(reach.source)
            .where(reach.limit)
            .where(Endpoint.host.in_(hosts))
            .group_by(Endpoint.host, Endpoint.endpoint_class)
        )
        out: dict[str, dict[str, int]] = {}
        for host, klass, n in rows.all():
            out.setdefault(host, {})[klass] = int(n)
        return out

    async def _host_chips(
        self, reach: _Reach, hosts: list[str]
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
            .select_from(reach.source)
            .where(reach.limit)
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
        """Each host's HTTP asset, a 200 first."""
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
                (HttpAsset.status_code == preds.HTTP_OK).desc().nulls_last(),
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
            query = query.where(~surface_endpoints.static_clause())
        return {host: int(n) for host, n in (await self.session.execute(query)).all()}

    async def pick(
        self, scope: ScopeLike, f: EndpointFilter, limit: int
    ) -> list[Endpoint]:
        """The rows a filter names, in relevance order, capped."""
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
        """Host summary and its parameters."""
        scope = QueryScope.of(scope)
        reach = [scope.match(Endpoint.scan_id), Endpoint.host == host]
        if hide_static:
            reach.append(~surface_endpoints.static_clause())

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
                    scope.match(Endpoint.scan_id),
                    Endpoint.host == host,
                    surface_endpoints.static_clause(),
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
        out.walled = await count(Endpoint.status_code.in_(preds.AUTH_STATUS))
        out.interesting = await count(
            func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0
        )
        out.new = await count(endpoint_is_new(scope))
        previous, previous_at = await self._previous_scan(scope)
        out.previous_scan_at = previous_at
        if previous is not None:
            gone_scope = [*_gone_from(previous, scope.single), Endpoint.host == host]
            if hide_static:
                gone_scope.append(~surface_endpoints.static_clause())
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
        named = element_counts(
            select(Endpoint.id).where(*reach), Endpoint.params, distinct=False
        ).subquery()
        rows = (await self.session.execute(select(named.c.value, named.c.n))).all()
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
        await self.session.execute(text(NO_JIT))
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
            bucket = status_bucket(r.status_code) if r.is_probed else "none"
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
        prior = QueryScope.of(previous)
        base = self._apply_filter(base, f.model_copy(update={"new": False}), prior)
        try:
            predicate = self._compiled(prior, f, now)
        except QuerySyntaxError as exc:
            return GonePage(error=syntax_error(exc))
        if predicate is not None:
            base = base.where(predicate)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
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
        config = await self.session.scalar(
            select(Scan.execution_config).where(Scan.id == scan_id)
        )
        config = config or {}
        query = select(Endpoint.path).where(
            Endpoint.scan_id == scan_id,
            Endpoint.host == body.host,
            Endpoint.is_probed.is_(False),
            Endpoint.endpoint_class.notin_(tuple(STATIC_CLASSES)),
        )
        query = self._apply_filter(
            query, EndpointFilter(dir_path=body.dir_path), QueryScope.of(scan_id)
        )
        scheme = PROBE_SCHEME.get(config.get("http_protocol"))
        if scheme:
            query = query.where(
                Endpoint.url.startswith(f"{scheme}://", autoescape=True)
            )
        excluded = config.get("excluded_paths") or []
        if excluded:
            paths = await self.session.stream_scalars(
                query.execution_options(yield_per=1000)
            )
            unverified = 0
            async for path in paths:
                if not matches_any(path, excluded):
                    unverified += 1
        else:
            unverified = int(
                await self.session.scalar(
                    select(func.count()).select_from(query.subquery())
                )
                or 0
            )
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
                urls_dropped=dict(row.urls_dropped or {}),
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
                    func.count().filter(Endpoint.is_probed.is_(True)).label("probed"),
                    func.count().filter(endpoint_status_class("2xx")).label("live"),
                    func.count().filter(Endpoint.param_count > 0).label("with_params"),
                    func.count()
                    .filter(func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0)
                    .label("interesting"),
                ).where(*reach)
            )
        ).one()
        total = int(row.total)
        if not total:
            return EndpointSummary(total=0, hosts=0)
        hosts = select(Endpoint.host).where(*reach).group_by(Endpoint.host).subquery()
        out = EndpointSummary(
            total=total,
            hosts=int(await self.session.scalar(select(func.count(hosts.c.host))) or 0),
        )
        fresh = None if host else await self._stored_new(scope)
        if fresh is None:
            fresh = await self.session.scalar(
                select(func.count()).where(*reach, endpoint_is_new(scope))
            )
        out.new = int(fresh or 0)
        out.probed = int(row.probed or 0)
        out.live = int(row.live or 0)
        out.with_params = int(row.with_params or 0)
        out.interesting = int(row.interesting or 0)

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
        by_class = await self.session.execute(
            select(Endpoint.endpoint_class, func.count())
            .where(*reach)
            .group_by(Endpoint.endpoint_class)
        )
        out.by_class = {k: int(v) for k, v in by_class.all()}
        sources = element_counts(
            select(Endpoint.id).where(*reach), Endpoint.sources
        ).subquery()
        by_source = await self.session.execute(select(sources.c.value, sources.c.n))
        out.by_source = {str(k): int(v) for k, v in by_source.all()}
        return out


def _evidence(row: Endpoint) -> list[SourceEvidence]:
    """Discovery evidence per source."""
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
