"""Shared identities across a scan's hosts, keyed by the Web Assets group-dimension columns."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.correlation import (
    COMMON_SHARE,
    CORRELATION_DEFAULT_KINDS,
    CORRELATION_KIND_HELP,
    CORRELATION_KIND_LABELS,
    CORRELATION_KIND_ORDER,
    MAX_GRAPH_HOSTS,
    MAX_HUBS_PER_KIND,
    MIN_BODY_BYTES,
    MIN_ESTATE_FOR_COMMON,
    MIN_SHARED,
    CorrelationKind,
)
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.scan_correlation import (
    CorrelationGraph,
    CorrelationHost,
    CorrelationHub,
    CorrelationKindStat,
)
from shared.models.subdomain import Subdomain
from shared.services.asset_query.groups import group_token
from shared.utils.infra import public_ca, shared_edge

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
    CorrelationKind.CERT.value: ("tls_fingerprint", "="),
    CorrelationKind.CERT_ISSUER.value: ("tls_issuer", "="),
    CorrelationKind.HEADERS.value: ("header_hash", "="),
}


def _values(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw if v not in (None, "")]
    text = str(raw)
    return [text] if text else []


def _platform(kind: str, value: str, cdn_addresses: dict[str, str]) -> str:
    """The provider whose tenants all carry this value."""
    if kind == CorrelationKind.IP.value:
        return cdn_addresses.get(value, "")
    if kind == CorrelationKind.CNAME.value:
        return shared_edge(value) or ""
    if kind == CorrelationKind.CERT_ISSUER.value:
        return public_ca(value) or ""
    return ""


def _label(kind: str, value: str) -> str:
    # keep both ends of a hash
    if kind in (
        CorrelationKind.BODY.value,
        CorrelationKind.JARM.value,
        CorrelationKind.FAVICON.value,
    ):
        return value if len(value) <= _HASH_LABEL else f"{value[:8]}…{value[-4:]}"
    return value if len(value) <= _LABEL_MAX else f"{value[: _LABEL_MAX - 1]}…"


def _hubs_of_kind(
    kind: str, values: dict[str, set[int]], cdn_addresses: dict[str, str]
) -> list[CorrelationHub]:
    """The hubs one kind contributes, most telling first."""
    # denominator: the hosts carrying this kind
    carriers = len({i for idx in values.values() for i in idx})
    candidates = []
    for value, idx in values.items():
        if len(idx) < MIN_SHARED:
            continue
        share = len(idx) / carriers if carriers else 0.0
        candidates.append(
            (
                value,
                sorted(idx),
                share,
                carriers >= MIN_ESTATE_FOR_COMMON and share >= COMMON_SHARE,
                _platform(kind, value, cdn_addresses),
            )
        )
    candidates.sort(key=lambda c: (bool(c[4]), c[3], -len(c[1]), c[0]))
    operator = {**_HOST_KINDS, **_ASSET_KINDS}[kind][1]
    return [
        CorrelationHub(
            id=f"{kind}:{value}",
            kind=kind,
            value=value,
            label=_label(kind, value),
            count=len(idx),
            share=round(share, 4),
            common=common,
            platform=bool(platform),
            platform_label=platform,
            query=group_token(kind, operator, value),
            members=idx,
        )
        for value, idx, share, common, platform in candidates[:MAX_HUBS_PER_KIND]
    ]


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
                .order_by(
                    Subdomain.http_status.is_(None),
                    Subdomain.is_active.is_(False),
                    Subdomain.name,
                )
                .limit(MAX_GRAPH_HOSTS + 1)
            )
        ).all()
        truncated = len(rows) > MAX_GRAPH_HOSTS
        rows = rows[:MAX_GRAPH_HOSTS]
        if not rows:
            return CorrelationGraph(kinds=self._kinds([], {}, 0))
        estate = await self._estate(project_id, scan_id) if truncated else len(rows)

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
                    HttpAsset.content_length,
                    *[getattr(HttpAsset, attr) for attr, _op in _ASSET_KINDS.values()],
                ).where(HttpAsset.scan_id == scan_id)
            )
        ).all()
        for asset in assets:
            i = index.get(asset.host)
            if i is None:
                continue
            thin = (asset.content_length or 0) < MIN_BODY_BYTES
            for kind, (attr, _op) in _ASSET_KINDS.items():
                if kind == CorrelationKind.BODY.value and thin:
                    continue
                for value in _values(getattr(asset, attr)):
                    members[kind][value].add(i)

        total = len(hosts)
        cdn_addresses = await self._cdn_addresses(scan_id)
        hubs: list[CorrelationHub] = []
        per_kind_hosts: dict[str, set[int]] = defaultdict(set)
        for kind in CORRELATION_KIND_ORDER:
            for hub in _hubs_of_kind(kind, members.get(kind, {}), cdn_addresses):
                hubs.append(hub)
                per_kind_hosts[kind].update(hub.members)

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
                hubs,
                {k: len(v) for k, v in per_kind_hosts.items()},
                total,
            ),
            total_hosts=total,
            estate_hosts=estate,
            shared_hosts=sum(1 for h in hosts if h.hubs),
            truncated=truncated,
        )

    async def _estate(self, project_id: UUID, scan_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Subdomain.id)).where(
                    Subdomain.project_id == project_id, Subdomain.scan_id == scan_id
                )
            )
            or 0
        )

    async def _cdn_addresses(self, scan_id: UUID) -> dict[str, str]:
        rows = (
            await self.session.execute(
                select(IpAddress.ip, IpAddress.cdn_name).where(
                    IpAddress.scan_id == scan_id, IpAddress.is_cdn.is_(True)
                )
            )
        ).all()
        return {ip: name or "CDN" for ip, name in rows}

    @staticmethod
    def _kinds(
        hubs: list[CorrelationHub], covered: dict[str, int], total: int
    ) -> list[CorrelationKindStat]:
        drawn: dict[str, list[CorrelationHub]] = defaultdict(list)
        for hub in hubs:
            drawn[hub.kind].append(hub)
        return [
            CorrelationKindStat(
                key=kind,
                label=CORRELATION_KIND_LABELS[kind],
                help=CORRELATION_KIND_HELP[kind],
                default=kind in CORRELATION_DEFAULT_KINDS,
                hubs=len(drawn[kind]),
                common=sum(1 for h in drawn[kind] if h.common),
                platform=sum(1 for h in drawn[kind] if h.platform),
                hosts=covered.get(kind, 0),
            )
            for kind in CORRELATION_KIND_ORDER
            if total == 0 or drawn[kind]
        ]
