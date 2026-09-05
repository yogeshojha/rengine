"""The site tree, built from the same filtered set the table shows.

Every node carries the drill-down token that reproduces it, so a node's count is always
the row count you land on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.endpoints import (
    ADMIN_INTERESTS,
    MAX_TREE_NODES,
    MAX_TREE_ROWS,
    SENSITIVE_INTERESTS,
    EndpointClass,
    PathInterest,
    folder_glyph,
)
from shared.models.endpoint import Endpoint, EndpointTree, TreeLeaf, TreeNode

_MERGED = "merged"
_HOST = "host"
_LEAF = "leaf"
_STATUS_BUCKETS = (
    ("2xx", 200, 300),
    ("3xx", 300, 400),
    ("4xx", 400, 500),
    ("5xx", 500, 600),
)


def _needs_quote(value: str) -> bool:
    return any(c in value for c in ' ()"[]:=><~') or not value


def _token(field: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = f'"{escaped}"' if _needs_quote(value) else value
    return f"{field}:{quoted}"


def _bucket(status: int | None) -> str:
    if status is None:
        return "none"
    for name, low, high in _STATUS_BUCKETS:
        if low <= status < high:
            return name
    return "none"


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
    hosts: set = field(default_factory=set)
    status_mix: dict = field(default_factory=dict)
    class_mix: dict = field(default_factory=dict)
    sources: set = field(default_factory=set)
    interest: set = field(default_factory=set)
    sample_url: str | None = None
    index_rows: list = field(default_factory=list)
    children: dict = field(default_factory=dict)

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
        if row.params:
            self.params += 1
        if row.endpoint_class == EndpointClass.API.value:
            self.api += 1
        self.sources.update(row.sources or ())
        self.interest.update(row.interest or ())
        if self.sample_url is None:
            self.sample_url = row.url


async def build_tree(session: AsyncSession, base, *, mode: str = _HOST) -> EndpointTree:
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

    nodes = [_emit(root, merged) for _, root in sorted(roots.items(), key=_root_order)]
    return EndpointTree(
        mode=mode,
        nodes=nodes,
        total_endpoints=len(rows),
        total_nodes=count,
        truncated=truncated or over_row_cap,
    )


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
    if node.kind == _HOST or node.children or not node.index_rows:
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


def _emit(node: _Node, merged: bool) -> TreeNode:
    """Collapse single-child chains the way a file tree does, so a deep path is one row."""
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

    children = [
        _emit(child, merged) for child in sorted(collapsed.children.values(), key=_rank)
    ]
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
        glyph=folder_glyph(collapsed.interest, collapsed.api, collapsed.subtree),
        sample_url=collapsed.sample_url,
        leaf=leaf,
        query=_token(field_name, value or "/"),
        children=children,
    )
