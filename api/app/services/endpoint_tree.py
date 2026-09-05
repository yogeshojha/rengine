"""The site tree, built from the same filtered set the table shows.

Every node carries the drill-down token that reproduces it, so a node's count is always
the row count you land on.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.asset_query import endpoint_is_new
from shared.definitions.endpoints import (
    ADMIN_INTERESTS,
    ARCHIVE_SOURCES,
    MAX_TREE_NODES,
    MAX_TREE_ROWS,
    SENSITIVE_INTERESTS,
    STATIC_CLASSES,
    STATIC_EXTENSIONS,
    EndpointClass,
    PathInterest,
    folder_glyph,
)
from shared.models.endpoint import Endpoint, EndpointTree, TreeLeaf, TreeNode

_MERGED = "merged"
_HOST = "host"
_LEAF = "leaf"
_GROUP = "group"
_AUTH_WALL = (401, 403)
_MIN_WALLED = 2
_MAX_OPEN_INSIDE = 2
_MIN_VERIFIED_FOR_ERROR = 10
_MAX_ERROR_SHARE = 0.1
_MIN_GROUP = 3
_MIN_SHARED = 2
_CORE_SHARE = 0.6
_MAX_HINT = 4
_MAX_GROUP_TOKEN = 40
_STATUS_BUCKETS = (
    ("2xx", 200, 300),
    ("3xx", 300, 400),
    ("4xx", 400, 500),
    ("5xx", 500, 600),
)


def static_clause():
    # coalesce keeps the predicate two-valued, or NOT drops every extension-less path
    return or_(
        Endpoint.endpoint_class.in_(tuple(STATIC_CLASSES)),
        func.coalesce(Endpoint.extension, "").in_(tuple(STATIC_EXTENSIONS)),
    )


def _needs_quote(value: str) -> bool:
    return any(c in value for c in ' ()"[]:=><~,') or not value


def _token(field: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = f'"{escaped}"' if _needs_quote(value) else value
    return f"{field}:{quoted}"


def _list_token(field: str, values: list[str]) -> str:
    items = [
        f'"{v.replace("\\", "\\\\").replace(chr(34), "\\" + chr(34))}"'
        if _needs_quote(v)
        else v
        for v in values
    ]
    return f"{field}:[{','.join(items)}]"


def _bucket(status: int | None) -> str:
    if status is None:
        return "none"
    for name, low, high in _STATUS_BUCKETS:
        if low <= status < high:
            return name
    return "none"


def anomaly_for(walled: int, opened: int, errors: int, verified: int) -> str | None:
    """The one sentence a folder's status mix earns, or nothing."""
    if walled >= _MIN_WALLED and 1 <= opened <= _MAX_OPEN_INSIDE:
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
        bucket = _bucket(row.status)
        self.status_mix[bucket] = self.status_mix.get(bucket, 0) + 1
        self.class_mix[row.endpoint_class] = (
            self.class_mix.get(row.endpoint_class, 0) + 1
        )
        if row.probed:
            self.verified += 1
        else:
            self.unprobed += 1
        if row.status in _AUTH_WALL:
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


async def build_tree(
    session: AsyncSession,
    base,
    *,
    scan_id: UUID,
    mode: str = _HOST,
    previous_scan_id: UUID | None = None,
    hide_static: bool = False,
) -> EndpointTree:
    """Aggregate the filtered endpoints into a directory tree.

    In host mode the roots are hosts. In merged mode paths are folded across hosts, which
    is what turns "/actuator/health" into one node that says it is on 40 hosts.
    """
    scoped = base.subquery()
    result = await session.execute(
        select(
            Endpoint.id,
            Endpoint.host,
            Endpoint.dir_path,
            Endpoint.path,
            Endpoint.url,
            Endpoint.status_code,
            Endpoint.is_probed,
            Endpoint.params,
            Endpoint.content_length,
            Endpoint.endpoint_class,
            Endpoint.sources,
            Endpoint.interest,
            endpoint_is_new(scan_id).label("is_new"),
        )
        .select_from(Endpoint)
        .join(scoped, Endpoint.id == scoped.c.id)
        .order_by(Endpoint.host, Endpoint.dir_path, Endpoint.path)
        .limit(MAX_TREE_ROWS + 1)
    )
    rows = [
        _Row(
            id=r.id,
            host=r.host,
            dir_path=r.dir_path,
            path=r.path,
            url=r.url,
            status=r.status_code,
            probed=r.is_probed,
            params=list(r.params or []),
            content_length=r.content_length,
            endpoint_class=r.endpoint_class,
            sources=list(r.sources or []),
            interest=list(r.interest or []),
            is_new=bool(r.is_new),
        )
        for r in result.all()
    ]
    if not rows:
        return EndpointTree(mode=mode)

    over_row_cap = len(rows) > MAX_TREE_ROWS
    if over_row_cap:
        rows = rows[:MAX_TREE_ROWS]

    merged = mode == _MERGED
    roots: dict[str, _Node] = {}
    count = 0
    truncated = False

    for row in rows:
        # the key is (host or "") + path so a client can rebuild it from the query alone
        prefix = "" if merged else row.host
        root_key = f"{prefix}/"
        root = roots.get(root_key)
        if root is None:
            root = _Node(
                key=root_key,
                name="All hosts" if merged else row.host,
                path="/",
                host=None if merged else row.host,
                depth=0,
                kind="directory" if merged else _HOST,
            )
            roots[root_key] = root
            count += 1
        cursor = root
        root.absorb(row)

        walked = ""
        complete = True
        for segment in [s for s in row.dir_path.split("/") if s]:
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
                    host=None if merged else row.host,
                    depth=cursor.depth + 1,
                )
                cursor.children[segment] = child
                count += 1
            child.absorb(row)
            cursor = child
        # only count it as living here if the walk actually reached its folder
        if complete:
            cursor.direct += 1
            if row.is_index:
                cursor.index_rows.append(row)

    if previous_scan_id is not None:
        await _count_gone(
            session,
            roots,
            scan_id=scan_id,
            previous_scan_id=previous_scan_id,
            hosts={r.host for r in rows},
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
    scan_id: UUID,
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
                current.scan_id == scan_id, current.signature == Endpoint.signature
            )
        ),
    )
    if hide_static:
        query = query.where(~static_clause())
    for host, dir_path in (await session.execute(query.limit(MAX_TREE_ROWS))).all():
        prefix = "" if merged else host
        cursor = roots.get(f"{prefix}/")
        if cursor is None:
            continue
        cursor.gone += 1
        for segment in [s for s in dir_path.split("/") if s]:
            child = cursor.children.get(segment)
            if child is None:
                break
            child.gone += 1
            cursor = child


def _root_order(item):
    _key, node = item
    return (-node.subtree, node.name)


def _rank(node: _Node) -> tuple:
    """Folders that matter sort first: exposed files, admin surfaces, API, then answering."""
    return (
        0 if node.interest & SENSITIVE_INTERESTS else 1,
        0 if node.interest & (ADMIN_INTERESTS | {PathInterest.AUTH.value}) else 1,
        0 if node.api else 1,
        0 if node.status_mix.get("2xx") else 1,
        -node.subtree,
        node.name,
    )


def _index_only(node: _Node) -> bool:
    """A folder whose only content is its own index reads as a leaf, the way Burp shows it."""
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
    """Siblings that share the same structural children fold into one group row.

    A WordPress multisite is sixteen folders each holding author/, wp-json/ and feed/;
    one row that says so beats sixteen that each say a little of it.
    """
    folders = [c for c in children if c.kind == "directory" and not _index_only(c)]
    if len(folders) < _MIN_GROUP:
        return children
    freq = Counter(name for c in folders for name in c.children)
    if not freq:
        return children
    # anchor on the most repeated child, then look for the skeleton shared by its carriers
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
    group.members = sorted(members, key=_rank)
    group.shared = [name for name, _ in inner.most_common() if name in core][:_MAX_HINT]
    member_keys = {m.key for m in members}
    return [group, *[c for c in children if c.key not in member_keys]]


def _emit(node: _Node) -> TreeNode:
    """Collapse single-child chains the way a file tree does, so a deep path is one row."""
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
        query=_token(field_name, value or "/"),
        children=children,
    )


def _emit_group(group: _Node) -> TreeNode:
    members = [_emit(m) for m in group.members]
    paths = [m.path for m in group.members][:_MAX_GROUP_TOKEN]
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
        glyph="group",
        sample_url=group.sample_url,
        leaf=None,
        query=_list_token("dir", paths),
        children=members,
        folders=len(members),
        top_folders=group.shared,
    )
