from collections import defaultdict
from uuid import UUID

from sqlalchemy import case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import resolved as host_resolved
from shared.models.hosting_flow import FlowLink, FlowNode, HostingFlow
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain

MAX_NETWORKS = 9
CLOUD = "cloud"
EDGE = "edge"
DIRECT = "direct"
UNKNOWN_ASN = 0

_FRONTING = {
    EDGE: ("CDN or WAF edge", "is:cdn"),
    CLOUD: ("Cloud provider", "is:cloud"),
    DIRECT: ("Direct to origin", "is:resolved and not is:cdn and not is:cloud"),
}
_SHORT_UPPER = 3


def _provider(name: str) -> str:
    return name.upper() if len(name) <= _SHORT_UPPER else name[:1].upper() + name[1:]


class HostingFlowService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_scan(self, project_id: UUID, scan_id: UUID) -> HostingFlow:
        web = (
            select(HttpAsset.host, HttpAsset.cdn_type, HttpAsset.asn, HttpAsset.asn_org)
            .where(HttpAsset.scan_id == scan_id)
            .distinct(HttpAsset.host)
            .order_by(HttpAsset.host, HttpAsset.discovered_at.desc())
            .subquery("web")
        )
        fronting = case(
            (Subdomain.is_cdn.is_(True), literal(EDGE)),
            (web.c.cdn_type == CLOUD, literal(CLOUD)),
            else_=literal(DIRECT),
        )
        asn = func.coalesce(Subdomain.asn, web.c.asn, UNKNOWN_ASN)
        asn_org = func.coalesce(Subdomain.asn_org, web.c.asn_org, literal(""))
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
                .group_by(
                    resolved,
                    fronting,
                    asn,
                    asn_org,
                    cdn,
                )
            )
        ).all()
        return _build(rows)


def _build(rows) -> HostingFlow:
    flow = HostingFlow()
    by_class: dict[str, int] = defaultdict(int)
    edge_names: dict[str, int] = defaultdict(int)
    by_network: dict[tuple[int, str], int] = defaultdict(int)
    class_to_network: dict[tuple[str, int, str], int] = defaultdict(int)
    for is_resolved, klass, asn, asn_org, cdn, n in rows:
        flow.hosts += n
        if not is_resolved:
            continue
        flow.resolving += n
        by_class[klass] += n
        if klass == EDGE and cdn:
            edge_names[cdn] += n
        key = (int(asn or 0), asn_org or "")
        by_network[key] += n
        class_to_network[(klass, *key)] += n
    if flow.resolving == 0:
        return flow

    flow.nodes.append(
        FlowNode(
            id="resolving",
            label="Resolving",
            count=flow.resolving,
            column=0,
            tone=DIRECT,
            query="is:resolved",
        )
    )
    for klass in (EDGE, CLOUD, DIRECT):
        n = by_class.get(klass, 0)
        if not n:
            continue
        label, query = _FRONTING[klass]
        if klass == EDGE and len(edge_names) == 1:
            label = f"{_provider(next(iter(edge_names)))} edge"
        flow.nodes.append(
            FlowNode(id=klass, label=label, count=n, column=1, tone=klass, query=query)
        )
        flow.links.append(
            FlowLink(source="resolving", target=klass, count=n, query=query)
        )

    ranked = sorted(by_network.items(), key=lambda kv: (-kv[1], kv[0][1]))
    top = ranked[:MAX_NETWORKS]
    rest = ranked[MAX_NETWORKS:]
    flow.networks = len(by_network)
    node_id: dict[tuple[int, str], str] = {}
    for (asn, org), n in top:
        nid = f"as{asn}" if asn else "as-unknown"
        node_id[(asn, org)] = nid
        dominant = max(
            (k for k in (EDGE, CLOUD, DIRECT) if class_to_network.get((k, asn, org))),
            key=lambda k: class_to_network[(k, asn, org)],
        )
        flow.nodes.append(
            FlowNode(
                id=nid,
                label=org or (f"AS{asn}" if asn else "Unknown network"),
                count=n,
                column=2,
                tone=dominant,
                query=f"asn:{asn}" if asn else None,
                detail=f"AS{asn}" if asn and org else None,
            )
        )
    if rest:
        known = [asn for (asn, _), _ in top if asn]
        flow.nodes.append(
            FlowNode(
                id="as-other",
                label="Other networks",
                count=sum(n for _, n in rest),
                column=2,
                tone="muted",
                query=(
                    "is:resolved and not ("
                    + " or ".join(f"asn:{a}" for a in known)
                    + ")"
                    if known
                    else None
                ),
                detail=f"{len(rest)} networks",
            )
        )
        for key, _ in rest:
            node_id[key] = "as-other"

    merged: dict[tuple[str, str], int] = defaultdict(int)
    for (klass, asn, org), n in class_to_network.items():
        merged[(klass, node_id[(asn, org)])] += n
    by_id = {node.id: node for node in flow.nodes}
    for (klass, target), n in merged.items():
        source_q = by_id[klass].query
        target_q = by_id[target].query
        flow.links.append(
            FlowLink(
                source=klass,
                target=target,
                count=n,
                query=f"{source_q} and {target_q}" if source_q and target_q else None,
            )
        )
    return flow
