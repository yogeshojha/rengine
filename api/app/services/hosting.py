from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import resolved as host_resolved
from shared.models.hosting import HostingComposition, HostingNetwork, HostingSlice
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain

MAX_NETWORKS = 6
CLOUD = "cloud"
EDGE = "edge"
DIRECT = "direct"
UNKNOWN_ASN = 0
ATTRIBUTED = "asn:>0"

_FRONTING = {
    EDGE: ("CDN or WAF edge", "is:cdn"),
    CLOUD: ("Cloud provider", "is:cloud"),
    DIRECT: ("Direct to origin", "is:resolved and not is:cdn and not is:cloud"),
}
_ORDER = (EDGE, CLOUD, DIRECT)
_SHORT_UPPER = 3

Labels = Mapping[str, tuple[str, str]]


def _provider(name: str) -> str:
    return name.upper() if len(name) <= _SHORT_UPPER else name[:1].upper() + name[1:]


class HostingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_scan(self, project_id: UUID, scan_id: UUID) -> HostingComposition:
        web = (
            select(
                HttpAsset.host.label("host"),
                func.bool_or(HttpAsset.cdn_type == CLOUD).label("cloud"),
            )
            .where(HttpAsset.scan_id == scan_id)
            .group_by(HttpAsset.host)
            .subquery("web")
        )
        fronting = case(
            (Subdomain.is_cdn.is_(True), literal(EDGE)),
            (web.c.cloud.is_(True), literal(CLOUD)),
            else_=literal(DIRECT),
        )
        asn = func.coalesce(Subdomain.asn, UNKNOWN_ASN)
        asn_org = func.coalesce(Subdomain.asn_org, literal(""))
        cdn = func.lower(func.coalesce(Subdomain.cdn_name, literal("")))
        resolved = host_resolved()
        rows = (
            await self.session.execute(
                select(
                    resolved.label("resolved"),
                    fronting.label("fronting"),
                    asn.label("asn"),
                    asn_org.label("asn_org"),
                    cdn.label("cdn"),
                    func.count().label("n"),
                )
                .select_from(Subdomain)
                .outerjoin(web, web.c.host == Subdomain.name)
                .where(Subdomain.scan_id == scan_id, Subdomain.project_id == project_id)
                .group_by(resolved, fronting, asn, asn_org, cdn)
            )
        ).all()
        return _build(rows)


def _slices(
    split: Mapping[str, int], labels: Labels, scope: str | None
) -> list[HostingSlice]:
    return [
        HostingSlice(
            kind=kind,
            label=labels[kind][0],
            count=split[kind],
            query=f"{scope} and {labels[kind][1]}" if scope else labels[kind][1],
        )
        for kind in _ORDER
        if split.get(kind)
    ]


def _build(rows) -> HostingComposition:
    out = HostingComposition()
    by_class: dict[str, int] = defaultdict(int)
    edge_names: dict[str, int] = defaultdict(int)
    by_network: dict[tuple[int, str], int] = defaultdict(int)
    per_network: dict[tuple[int, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    unattributed: dict[str, int] = defaultdict(int)
    for is_resolved, klass, asn, asn_org, cdn, n in rows:
        out.hosts += n
        if not is_resolved:
            continue
        out.resolving += n
        by_class[klass] += n
        if klass == EDGE and cdn:
            edge_names[cdn] += n
        number = int(asn or UNKNOWN_ASN)
        if not number:
            unattributed[klass] += n
            continue
        out.attributed += n
        key = (number, asn_org or "")
        by_network[key] += n
        per_network[key][klass] += n
    if out.resolving == 0:
        return out

    labels = dict(_FRONTING)
    if len(edge_names) == 1:
        labels[EDGE] = (f"{_provider(next(iter(edge_names)))} edge", _FRONTING[EDGE][1])
    out.fronting = _slices(by_class, labels, None)

    out.networks = len(by_network)
    ranked = sorted(by_network.items(), key=lambda kv: (-kv[1], kv[0][1]))
    top, rest = ranked[:MAX_NETWORKS], ranked[MAX_NETWORKS:]
    for (number, org), n in top:
        scope = f"asn:{number}"
        out.by_network.append(
            HostingNetwork(
                id=f"as{number}",
                label=org or f"AS{number}",
                detail=f"AS{number}" if org else None,
                count=n,
                query=scope,
                fronting=_slices(per_network[(number, org)], labels, scope),
            )
        )
    if rest:
        drawn = " or ".join(f"asn:{number}" for (number, _), _ in top)
        scope = f"{ATTRIBUTED} and not ({drawn})" if drawn else ATTRIBUTED
        split: dict[str, int] = defaultdict(int)
        for key, _ in rest:
            for kind, n in per_network[key].items():
                split[kind] += n
        out.by_network.append(
            HostingNetwork(
                id="other",
                label="Other networks",
                detail=f"{len(rest)} network{'' if len(rest) == 1 else 's'}",
                count=sum(n for _, n in rest),
                query=scope,
                fronting=_slices(split, labels, scope),
            )
        )
    if unattributed and out.attributed:
        scope = f"is:resolved and not {ATTRIBUTED}"
        out.by_network.append(
            HostingNetwork(
                id="unattributed",
                label="Network not attributed",
                count=sum(unattributed.values()),
                query=scope,
                fronting=_slices(unattributed, labels, scope),
            )
        )
    return out
