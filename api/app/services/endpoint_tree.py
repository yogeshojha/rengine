from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Text, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from shared.definitions.endpoints import (
    ADMIN_INTERESTS,
    ARCHIVE_SOURCES,
    MAX_TREE_NODES,
    MAX_TREE_ROWS,
    SENSITIVE_INTERESTS,
    EndpointClass,
    FolderGlyph,
    PathInterest,
    folder_glyph,
)
from shared.models.endpoint import Endpoint, EndpointTree, TreeLeaf, TreeNode
from shared.services.asset_query import QueryScope, endpoint_is_new
from shared.services.asset_query import predicates as preds
from shared.services.asset_query.tokens import list_token, token
from shared.services.surface_query.endpoints import static_clause

_MERGED = "merged"
_HOST = "host"
_LEAF = "leaf"
_GROUP = FolderGlyph.GROUP.value
MIN_WALLED = 2
MAX_OPEN_INSIDE = 2
_MIN_VERIFIED_FOR_ERROR = 10
_MAX_ERROR_SHARE = 0.1
_MIN_GROUP = 3
_MIN_SHARED = 2
_CORE_SHARE = 0.6
_MAX_HINT = 4
_MAX_GROUP_TOKEN = 40


def status_bucket(status: int | None) -> str:
    if status is None:
        return "none"
    for name, (low, high) in preds.STATUS_BUCKETS.items():
        if low <= status < high:
            return name
    return "none"


def anomaly_for(walled: int, opened: int, errors: int, verified: int) -> str | None:
    """Status-mix anomaly text for a folder, or None."""
    if walled >= MIN_WALLED and 1 <= opened <= MAX_OPEN_INSIDE:
        return (
            f"{opened} of {walled + opened} {'answers' if opened == 1 else 'answer'} "
            "without auth"
        )
    if (
        errors
        and verified >= _MIN_VERIFIED_FOR_ERROR
        and errors / verified <= _MAX_ERROR_SHARE
    ):
        return f"{errors} of {verified} {'returns' if errors == 1 else 'return'} a server error"
    return None


def archive_only_for(sources: set[str], status_mix: dict[str, int]) -> bool:
    return (
        bool(sources)
        and sources <= ARCHIVE_SOURCES
        and not (status_mix.get("2xx") or status_mix.get("3xx"))
    )


@dataclass
class _Row:
    id: object
    host: str
    dir_path: str
    path: str
    url: str
    status: int | None
    probed: bool
    params: list
    content_length: int | None
    endpoint_class: str
    sources: list
    interest: list
    is_new: bool

    @property
    def is_index(self) -> bool:
        return self.path == self.dir_path

    @property
    def shape(self) -> tuple:
        return (self.path, tuple(self.params))


@dataclass
class _Node:
    key: str
    name: str
    path: str
    host: str | None
    depth: int
    kind: str = "directory"
    direct: int = 0
    subtree: int = 0
    unprobed: int = 0
    verified: int = 0
    params: int = 0
    api: int = 0
    new: int = 0
    gone: int = 0
    walled: int = 0
    hosts: set = field(default_factory=set)
    status_mix: dict = field(default_factory=dict)
    class_mix: dict = field(default_factory=dict)
    sources: set = field(default_factory=set)
    interest: set = field(default_factory=set)
    sample_url: str | None = None
    index_rows: list = field(default_factory=list)
    children: dict = field(default_factory=dict)
    members: list = field(default_factory=list)
    shared: list = field(default_factory=list)

    def absorb(self, row: _Row) -> None:
        self.subtree += 1
        self.hosts.add(row.host)
        bucket = status_bucket(row.status)
        self.status_mix[bucket] = self.status_mix.get(bucket, 0) + 1
        self.class_mix[row.endpoint_class] = (
            self.class_mix.get(row.endpoint_class, 0) + 1
        )
        if row.probed:
            self.verified += 1
        else:
            self.unprobed += 1
        if row.status in preds.AUTH_STATUS:
            self.walled += 1
        if row.params:
            self.params += 1
        if row.endpoint_class == EndpointClass.API.value:
            self.api += 1
        if row.is_new:
            self.new += 1
        self.sources.update(row.sources or ())
        self.interest.update(row.interest or ())
        if self.sample_url is None:
            self.sample_url = row.url

    def merge(self, other: _Node) -> None:
        """Fold a sibling into a synthetic group node."""
        self.subtree += other.subtree
        self.unprobed += other.unprobed
        self.verified += other.verified
        self.params += other.params
        self.api += other.api
        self.new += other.new
        self.gone += other.gone
        self.walled += other.walled
        self.hosts |= other.hosts
        for k, v in other.status_mix.items():
            self.status_mix[k] = self.status_mix.get(k, 0) + v
        for k, v in other.class_mix.items():
            self.class_mix[k] = self.class_mix.get(k, 0) + v
        self.sources |= other.sources
        self.interest |= other.interest
        if self.sample_url is None:
            self.sample_url = other.sample_url


@dataclass
class _Run:
    """Consecutive rows of one folder on one host."""

    host: str
    dir_path: str
    url: str
    n: int = 0
    unprobed: int = 0
    verified: int = 0
    params: int = 0
    api: int = 0
    new: int = 0
    walled: int = 0
    status_mix: dict = field(default_factory=dict)
    class_mix: dict = field(default_factory=dict)
    sources: set = field(default_factory=set)
    interest: set = field(default_factory=set)
    index_rows: list = field(default_factory=list)


def _absorb_run(node: _Node, run: _Run) -> None:
    node.subtree += run.n
    node.hosts.add(run.host)
    for k, v in run.status_mix.items():
        node.status_mix[k] = node.status_mix.get(k, 0) + v
    for k, v in run.class_mix.items():
        node.class_mix[k] = node.class_mix.get(k, 0) + v
    node.verified += run.verified
    node.unprobed += run.unprobed
    node.walled += run.walled
    node.params += run.params
    node.api += run.api
    node.new += run.new
    node.sources |= run.sources
    node.interest |= run.interest
    if node.sample_url is None:
        node.sample_url = run.url


def _runs(rows) -> list[_Run]:
    """Fold consecutive rows that share a host and a folder."""
    decoded: dict[str | None, list] = {None: []}
    buckets: dict[int | None, str] = {}
    api = EndpointClass.API.value
    auth = frozenset(preds.AUTH_STATUS)
    out: list[_Run] = []
    run: _Run | None = None
    for (
        row_id,
        host,
        dir_path,
        path,
        url,
        status,
        probed,
        params_text,
        content_length,
        klass,
        sources_text,
        interest_text,
        is_new,
    ) in rows:
        if run is None or host != run.host or dir_path != run.dir_path:
            run = _Run(host=host, dir_path=dir_path, url=url)
            out.append(run)
        params = decoded.get(params_text)
        if params is None:
            params = decoded[params_text] = json.loads(params_text) or []
        sources = decoded.get(sources_text)
        if sources is None:
            sources = decoded[sources_text] = json.loads(sources_text) or []
        interest = decoded.get(interest_text)
        if interest is None:
            interest = decoded[interest_text] = json.loads(interest_text) or []
        bucket = buckets.get(status)
        if bucket is None:
            bucket = buckets[status] = status_bucket(status)
        run.n += 1
        run.status_mix[bucket] = run.status_mix.get(bucket, 0) + 1
        run.class_mix[klass] = run.class_mix.get(klass, 0) + 1
        if probed:
            run.verified += 1
        else:
            run.unprobed += 1
        if status in auth:
            run.walled += 1
        if params:
            run.params += 1
        if klass == api:
            run.api += 1
        if is_new:
            run.new += 1
        if sources:
            run.sources.update(sources)
        if interest:
            run.interest.update(interest)
        if path == dir_path:
            run.index_rows.append(
                _Row(
                    id=row_id,
                    host=host,
                    dir_path=dir_path,
                    path=path,
                    url=url,
                    status=status,
                    probed=probed,
                    params=list(params),
                    content_length=content_length,
                    endpoint_class=klass,
                    sources=list(sources),
                    interest=list(interest),
                    is_new=bool(is_new),
                )
            )
    return out


async def build_tree(
    session: AsyncSession,
    base,
    *,
    scope: QueryScope,
    mode: str = _HOST,
    previous_scan_id: UUID | None = None,
    hide_static: bool = False,
) -> EndpointTree:
    """Aggregate the filtered endpoints into a directory tree."""
    connection = await session.connection()
    result = await connection.execute(
        base.with_only_columns(
            Endpoint.id,
            Endpoint.host,
            Endpoint.dir_path,
            Endpoint.path,
            Endpoint.url,
            Endpoint.status_code,
            Endpoint.is_probed,
            cast(Endpoint.params, Text).label("params"),
            Endpoint.content_length,
            Endpoint.endpoint_class,
            cast(Endpoint.sources, Text).label("sources"),
            cast(Endpoint.interest, Text).label("interest"),
            endpoint_is_new(scope).label("is_new"),
        )
        .order_by(Endpoint.host, Endpoint.dir_path, Endpoint.path)
        .limit(MAX_TREE_ROWS + 1)
    )
    rows = result.all()
    if not rows:
        return EndpointTree(mode=mode)

    over_row_cap = len(rows) > MAX_TREE_ROWS
    if over_row_cap:
        rows = rows[:MAX_TREE_ROWS]

    merged = mode == _MERGED
    roots: dict[str, _Node] = {}
    count = 0
    truncated = False
    hosts: set[str] = set()

    for run in _runs(rows):
        hosts.add(run.host)
        prefix = "" if merged else run.host
        root_key = f"{prefix}/"
        root = roots.get(root_key)
        if root is None:
            root = _Node(
                key=root_key,
                name="All hosts" if merged else run.host,
                path="/",
                host=None if merged else run.host,
                depth=0,
                kind="directory" if merged else _HOST,
            )
            roots[root_key] = root
            count += 1
        cursor = root
        _absorb_run(root, run)

        walked = ""
        complete = True
        for segment in [s for s in run.dir_path.split("/") if s]:
            walked = f"{walked}/{segment}"
            child = cursor.children.get(segment)
            if child is None:
                if count >= MAX_TREE_NODES:
                    truncated = True
                    complete = False
                    break
                child = _Node(
                    key=f"{prefix}{walked}/",
                    name=segment,
                    path=f"{walked}/",
                    host=None if merged else run.host,
                    depth=cursor.depth + 1,
                )
                cursor.children[segment] = child
                count += 1
            _absorb_run(child, run)
            cursor = child
        if complete:
            cursor.direct += run.n
            cursor.index_rows.extend(run.index_rows)

    if previous_scan_id is not None:
        await _count_gone(
            session,
            roots,
            scope=scope,
            previous_scan_id=previous_scan_id,
            hosts=hosts,
            merged=merged,
            hide_static=hide_static,
        )

    nodes = [_emit(root) for _, root in sorted(roots.items(), key=_root_order)]
    return EndpointTree(
        mode=mode,
        nodes=nodes,
        total_endpoints=len(rows),
        total_nodes=count,
        truncated=truncated or over_row_cap,
    )


async def _count_gone(
    session: AsyncSession,
    roots: dict[str, _Node],
    *,
    scope: QueryScope,
    previous_scan_id: UUID,
    hosts: set[str],
    merged: bool,
    hide_static: bool,
) -> None:
    """Paths the previous scan had that this one lost, counted onto the nearest surviving folder."""
    current = aliased(Endpoint)
    query = select(Endpoint.host, Endpoint.dir_path).where(
        Endpoint.scan_id == previous_scan_id,
        Endpoint.host.in_(sorted(hosts)),
        ~exists(
            select(1).where(
                scope.match(current.scan_id),
                current.signature == Endpoint.signature,
            )
        ),
    )
    if hide_static:
        query = query.where(~static_clause())
    lost = query.limit(MAX_TREE_ROWS).subquery()
    grouped = select(lost.c.host, lost.c.dir_path, func.count()).group_by(
        lost.c.host, lost.c.dir_path
    )
    for host, dir_path, n in (await session.execute(grouped)).all():
        prefix = "" if merged else host
        cursor = roots.get(f"{prefix}/")
        if cursor is None:
            continue
        cursor.gone += n
        for segment in [s for s in dir_path.split("/") if s]:
            child = cursor.children.get(segment)
            if child is None:
                break
            child.gone += n
            cursor = child


def _root_order(item):
    _key, node = item
    return (-node.subtree, node.name)


def _rank(node: _Node) -> tuple:
    """Sort key: sensitive, admin, API, answering, size, name."""
    return (
        0 if node.interest & SENSITIVE_INTERESTS else 1,
        0 if node.interest & (ADMIN_INTERESTS | {PathInterest.AUTH.value}) else 1,
        0 if node.api else 1,
        0 if node.status_mix.get("2xx") else 1,
        -node.subtree,
        node.name,
    )


def _index_only(node: _Node) -> bool:
    """A folder whose only content is its own index reads as a leaf."""
    if node.kind != "directory" or node.children or not node.index_rows:
        return False
    if len(node.index_rows) != node.direct:
        return False
    return len({row.shape for row in node.index_rows}) == 1


def _leaf(row: _Row) -> TreeLeaf:
    return TreeLeaf(
        id=row.id,
        url=row.url,
        host=row.host,
        path=row.path,
        params=list(row.params),
        param_count=len(row.params),
        endpoint_class=row.endpoint_class,
        is_probed=row.probed,
        status_code=row.status,
        content_length=row.content_length,
        sources=list(row.sources),
        interest=list(row.interest),
    )


def _fold_layouts(parent: _Node, children: list[_Node]) -> list[_Node]:
    """Siblings that share the same structural children fold into one group row."""
    folders = [c for c in children if c.kind == "directory" and not _index_only(c)]
    if len(folders) < _MIN_GROUP:
        return children
    freq = Counter(name for c in folders for name in c.children)
    if not freq:
        return children
    anchor, carriers = freq.most_common(1)[0]
    if carriers < _MIN_GROUP:
        return children
    pool = [c for c in folders if anchor in c.children]
    inner = Counter(name for c in pool for name in c.children)
    threshold = max(_MIN_GROUP, int(len(pool) * _CORE_SHARE))
    core = {name for name, n in inner.items() if n >= threshold}
    if len(core) < _MIN_SHARED:
        return children
    members = [c for c in pool if len(set(c.children) & core) >= _MIN_SHARED]
    if len(members) < _MIN_GROUP:
        return children
    members = sorted(members, key=_rank)[:_MAX_GROUP_TOKEN]
    group = _Node(
        key=f"{parent.key}#layout",
        name=f"{len(members)} folders share one layout",
        path=parent.path,
        host=parent.host,
        depth=parent.depth + 1,
        kind=_GROUP,
    )
    for m in members:
        group.merge(m)
    group.members = members
    group.shared = [name for name, _ in inner.most_common() if name in core][:_MAX_HINT]
    member_keys = {m.key for m in members}
    return [group, *[c for c in children if c.key not in member_keys]]


def _emit(node: _Node) -> TreeNode:
    """Collapse single-child chains."""
    if node.kind == _GROUP:
        return _emit_group(node)
    collapsed = node
    name_parts = [node.name]
    while (
        collapsed.direct == 0
        and len(collapsed.children) == 1
        and collapsed.kind != _HOST
    ):
        only = next(iter(collapsed.children.values()))
        name_parts.append(only.name)
        collapsed = only

    ordered = sorted(collapsed.children.values(), key=_rank)
    children = [_emit(child) for child in _fold_layouts(collapsed, ordered)]
    field_name = "host" if collapsed.kind == _HOST else "dir"
    value = collapsed.host if collapsed.kind == _HOST else collapsed.path
    kind = collapsed.kind
    leaf = None
    name = "/".join(name_parts)
    if _index_only(collapsed):
        kind = _LEAF
        leaf = _leaf(collapsed.index_rows[0])
        name = f"{name}/"
    return TreeNode(
        key=collapsed.key,
        name=name,
        path=collapsed.path,
        host=collapsed.host,
        kind=kind,
        depth=node.depth,
        direct_count=collapsed.direct,
        subtree_count=collapsed.subtree,
        child_count=len(children),
        hosts=len(collapsed.hosts),
        status_mix=dict(sorted(collapsed.status_mix.items())),
        class_mix=dict(sorted(collapsed.class_mix.items())),
        sources=sorted(collapsed.sources),
        interest=sorted(collapsed.interest),
        has_params=collapsed.params > 0,
        params=collapsed.params,
        verified=collapsed.verified,
        unprobed=collapsed.unprobed,
        new_count=collapsed.new,
        gone_count=node.gone,
        anomaly=anomaly_for(
            collapsed.walled,
            collapsed.status_mix.get("2xx", 0),
            collapsed.status_mix.get("5xx", 0),
            collapsed.verified,
        ),
        archive_only=archive_only_for(collapsed.sources, collapsed.status_mix),
        glyph=folder_glyph(collapsed.interest, collapsed.api, collapsed.subtree),
        sample_url=collapsed.sample_url,
        leaf=leaf,
        query=token(field_name, ":", value or "/"),
        children=children,
    )


def _emit_group(group: _Node) -> TreeNode:
    members = [_emit(m) for m in group.members]
    paths = [m.path for m in group.members]
    return TreeNode(
        key=group.key,
        name=group.name,
        path=group.path,
        host=group.host,
        kind=_GROUP,
        depth=group.depth,
        direct_count=0,
        subtree_count=group.subtree,
        child_count=len(members),
        hosts=len(group.hosts),
        status_mix=dict(sorted(group.status_mix.items())),
        class_mix=dict(sorted(group.class_mix.items())),
        sources=sorted(group.sources),
        interest=sorted(group.interest),
        has_params=group.params > 0,
        params=group.params,
        verified=group.verified,
        unprobed=group.unprobed,
        new_count=group.new,
        gone_count=group.gone,
        anomaly=None,
        archive_only=archive_only_for(group.sources, group.status_mix),
        glyph=FolderGlyph.GROUP.value,
        sample_url=group.sample_url,
        leaf=None,
        query=list_token("dir", paths),
        children=members,
        folders=len(members),
        top_folders=group.shared,
    )
