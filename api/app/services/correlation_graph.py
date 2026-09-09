"""Shared identities across a scan's hosts, keyed by the Web Assets group-dimension columns."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.correlation import (
    COMMON_SHARE,
    CORRELATION_DEFAULT_KINDS,
    CORRELATION_KIND_HELP,
    CORRELATION_KIND_LABELS,
    CORRELATION_KIND_ORDER,
    MAX_GRAPH_HOSTS,
    MAX_HUBS_PER_KIND,
    MIN_SHARED,
    CorrelationKind,
)
from shared.models.http_asset import HttpAsset
from shared.models.scan_correlation import (
    CorrelationGraph,
    CorrelationHost,
    CorrelationHub,
    CorrelationKindStat,
)
from shared.models.subdomain import Subdomain
from shared.services.asset_query.groups import group_token

_HTTP_OK = 200
_HTTP_CLIENT = 400
_LABEL_MAX = 60
_HASH_LABEL = 14

# source column and token operator per kind
_HOST_KINDS: dict[str, tuple[str, str]] = {
    CorrelationKind.IP.value: ("resolved_ips", ":"),
    CorrelationKind.CNAME.value: ("cname", "="),
    CorrelationKind.TITLE.value: ("page_title", "="),
    CorrelationKind.FAVICON.value: ("favicon_hash", "="),
    CorrelationKind.TECH.value: ("tech", "="),
    CorrelationKind.SERVER.value: ("webserver", "="),
    CorrelationKind.CDN.value: ("cdn_name", "="),
}
_ASSET_KINDS: dict[str, tuple[str, str]] = {
    CorrelationKind.BODY.value: ("content_hash", "="),
    CorrelationKind.JARM.value: ("jarm", "="),
    CorrelationKind.CERT_ISSUER.value: ("tls_issuer", "="),
}


def _values(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw if v not in (None, "")]
    text = str(raw)
    return [text] if text else []


def _label(kind: str, value: str) -> str:
    # keep both ends of a hash
    if kind in (
        CorrelationKind.BODY.value,
        CorrelationKind.JARM.value,
        CorrelationKind.FAVICON.value,
    ):
        return value if len(value) <= _HASH_LABEL else f"{value[:8]}…{value[-4:]}"
    return value if len(value) <= _LABEL_MAX else f"{value[: _LABEL_MAX - 1]}…"


class CorrelationGraphService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build(self, project_id: UUID, scan_id: UUID) -> CorrelationGraph:
        rows = (
            await self.session.execute(
                select(
                    Subdomain.id,
                    Subdomain.name,
                    Subdomain.is_active,
                    Subdomain.http_status,
                    Subdomain.page_title,
                    Subdomain.resolved_ips,
                    Subdomain.cname,
                    Subdomain.favicon_hash,
                    Subdomain.tech,
                    Subdomain.webserver,
                    Subdomain.cdn_name,
                )
                .where(Subdomain.project_id == project_id, Subdomain.scan_id == scan_id)
                .order_by(Subdomain.name)
                .limit(MAX_GRAPH_HOSTS + 1)
            )
        ).all()
        truncated = len(rows) > MAX_GRAPH_HOSTS
        rows = rows[:MAX_GRAPH_HOSTS]
        if not rows:
            return CorrelationGraph(kinds=self._kinds({}, {}, 0))

        index = {row.name: i for i, row in enumerate(rows)}
        hosts = [
            CorrelationHost(
                id=row.id,
                name=row.name,
                live=row.http_status is not None
                and _HTTP_OK <= row.http_status < _HTTP_CLIENT,
                status=row.http_status,
                title=row.page_title,
            )
            for row in rows
        ]

        members: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
        for i, row in enumerate(rows):
            for kind, (attr, _op) in _HOST_KINDS.items():
                for value in _values(getattr(row, attr)):
                    members[kind][value].add(i)

        assets = (
            await self.session.execute(
                select(
                    HttpAsset.host,
                    HttpAsset.content_hash,
                    HttpAsset.jarm,
                    HttpAsset.tls_issuer,
                ).where(HttpAsset.scan_id == scan_id)
            )
        ).all()
        for asset in assets:
            i = index.get(asset.host)
            if i is None:
                continue
            for kind, (attr, _op) in _ASSET_KINDS.items():
                for value in _values(getattr(asset, attr)):
                    members[kind][value].add(i)

        total = len(hosts)
        hubs: list[CorrelationHub] = []
        per_kind_hubs: dict[str, int] = defaultdict(int)
        per_kind_common: dict[str, int] = defaultdict(int)
        per_kind_hosts: dict[str, set[int]] = defaultdict(set)
        ops = {**_HOST_KINDS, **_ASSET_KINDS}
        for kind in CORRELATION_KIND_ORDER:
            shared = [
                (value, sorted(idx))
                for value, idx in members.get(kind, {}).items()
                if len(idx) >= MIN_SHARED
            ]
            shared.sort(key=lambda x: (-len(x[1]), x[0]))
            for value, idx in shared[:MAX_HUBS_PER_KIND]:
                share = len(idx) / total
                common = share >= COMMON_SHARE
                per_kind_hubs[kind] += 1
                if common:
                    per_kind_common[kind] += 1
                per_kind_hosts[kind].update(idx)
                hubs.append(
                    CorrelationHub(
                        id=f"{kind}:{value}",
                        kind=kind,
                        value=value,
                        label=_label(kind, value),
                        count=len(idx),
                        share=round(share, 4),
                        common=common,
                        query=group_token(kind, ops[kind][1], value),
                        members=idx,
                    )
                )

        degree: dict[int, int] = defaultdict(int)
        for hub in hubs:
            for i in hub.members:
                degree[i] += 1
        for i, host in enumerate(hosts):
            host.hubs = degree.get(i, 0)

        return CorrelationGraph(
            hosts=hosts,
            hubs=hubs,
            kinds=self._kinds(
                {k: (per_kind_hubs[k], per_kind_common[k]) for k in per_kind_hubs},
                {k: len(v) for k, v in per_kind_hosts.items()},
                total,
            ),
            total_hosts=total,
            shared_hosts=sum(1 for h in hosts if h.hubs),
            truncated=truncated,
        )

    @staticmethod
    def _kinds(
        counts: dict[str, tuple[int, int]], covered: dict[str, int], total: int
    ) -> list[CorrelationKindStat]:
        return [
            CorrelationKindStat(
                key=kind,
                label=CORRELATION_KIND_LABELS[kind],
                help=CORRELATION_KIND_HELP[kind],
                default=kind in CORRELATION_DEFAULT_KINDS,
                hubs=counts.get(kind, (0, 0))[0],
                common=counts.get(kind, (0, 0))[1],
                hosts=covered.get(kind, 0),
            )
            for kind in CORRELATION_KIND_ORDER
            if total == 0 or counts.get(kind, (0, 0))[0] > 0
        ]
