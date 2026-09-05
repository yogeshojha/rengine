"""The site tree, built from the same filtered set the table shows.

Every node carries the drill-down token that reproduces it, so a node's count is always
the row count you land on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.endpoints import MAX_TREE_NODES, MAX_TREE_ROWS
from shared.models.endpoint import Endpoint, EndpointTree, TreeNode

_MERGED = "merged"
_HOST = "host"
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
    host: str
    dir_path: str
    path: str
    url: str
    status: int | None
    probed: bool
    params: int
    sources: list
    interest: list


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
    has_params: bool = False
    hosts: set = field(default_factory=set)
    status_mix: dict = field(default_factory=dict)
    sources: set = field(default_factory=set)
    interest: set = field(default_factory=set)
    sample_url: str | None = None
    children: dict = field(default_factory=dict)

    def absorb(self, row: _Row) -> None:
        self.subtree += 1
        self.hosts.add(row.host)
        bucket = _bucket(row.status)
        self.status_mix[bucket] = self.status_mix.get(bucket, 0) + 1
        if not row.probed:
            self.unprobed += 1
        if row.params:
            self.has_params = True
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
            Endpoint.host,
            Endpoint.dir_path,
            Endpoint.path,
            Endpoint.url,
            Endpoint.status_code,
            Endpoint.is_probed,
            Endpoint.param_count,
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
            host=r.host,
            dir_path=r.dir_path,
            path=r.path,
            url=r.url,
            status=r.status_code,
            probed=r.is_probed,
            params=r.param_count,
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
        _emit(child, merged)
        for child in sorted(
            collapsed.children.values(), key=lambda c: (-c.subtree, c.name)
        )
    ]
    field_name = "host" if collapsed.kind == _HOST else "dir"
    value = collapsed.host if collapsed.kind == _HOST else collapsed.path
    return TreeNode(
        key=collapsed.key,
        name="/".join(name_parts),
        path=collapsed.path,
        host=collapsed.host,
        kind=collapsed.kind,
        depth=node.depth,
        direct_count=collapsed.direct,
        subtree_count=collapsed.subtree,
        child_count=len(children),
        hosts=len(collapsed.hosts),
        status_mix=dict(sorted(collapsed.status_mix.items())),
        sources=sorted(collapsed.sources),
        interest=sorted(collapsed.interest),
        has_params=collapsed.has_params,
        unprobed=collapsed.unprobed,
        sample_url=collapsed.sample_url,
        query=_token(field_name, value or "/"),
        children=children,
    )
