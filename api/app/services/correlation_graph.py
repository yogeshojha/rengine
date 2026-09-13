"""The shared-identity graph for a scope: one scan, or every target's covering scan."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.target_names import target_names
from shared.definitions.correlation import (
    CORRELATION_DEFAULT_KINDS,
    CORRELATION_KIND_HELP,
    CORRELATION_KIND_LABELS,
    CORRELATION_KIND_ORDER,
    MAX_GRAPH_HOSTS,
)
from shared.models.scan_correlation import (
    CorrelationGraph,
    CorrelationHost,
    CorrelationHub,
    CorrelationKindStat,
)
from shared.models.subdomain import Subdomain
from shared.services.asset_query.scope import QueryScope, ScopeLike
from shared.services.correlation import CorrelationFinder, Hub, Member

_HTTP_OK = 200
_HTTP_CLIENT = 400


def _rank(member: Member) -> tuple:
    """Answered first, then active, then by name."""
    return (member.status is None, not member.active, member.name)


class CorrelationGraphService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build(self, scope: ScopeLike) -> CorrelationGraph:
        scope = QueryScope.of(scope)
        if not scope:
            return CorrelationGraph(kinds=_kinds([], {}, 0, {}))
        found = await CorrelationFinder(self.session).find(scope)
        estate = await self._estate(scope)
        carrying: dict[UUID, Member] = {}
        for hub in found.hubs:
            for member in hub.members:
                carrying.setdefault(member.id, member)
        if not carrying:
            return CorrelationGraph(
                kinds=_kinds([], {}, 0, found.discovered),
                estate_hosts=estate,
                targets_total=len(scope.ids),
            )

        ranked = sorted(carrying.values(), key=_rank)
        drawn = ranked[:MAX_GRAPH_HOSTS]
        index = {member.id: i for i, member in enumerate(drawn)}
        names = (
            await target_names(self.session, (m.target_id for m in drawn))
            if len(scope.ids) > 1
            else {}
        )
        hosts = [
            CorrelationHost(
                id=member.id,
                name=member.name,
                live=member.status is not None
                and _HTTP_OK <= member.status < _HTTP_CLIENT,
                status=member.status,
                title=member.title,
                target=names.get(member.target_id, ""),
            )
            for member in drawn
        ]

        hubs = [
            hub
            for hub in (_hub(found_hub, index) for found_hub in found.hubs)
            if hub is not None
        ]
        for hub in hubs:
            for i in hub.members:
                hosts[i].hubs += 1

        per_kind: dict[str, int] = {}
        for kind in CORRELATION_KIND_ORDER:
            members = {i for hub in hubs if hub.kind == kind for i in hub.members}
            if members:
                per_kind[kind] = len(members)
        return CorrelationGraph(
            hosts=hosts,
            hubs=hubs,
            kinds=_kinds(hubs, per_kind, len(hosts), found.discovered),
            total_hosts=len(hosts),
            estate_hosts=estate,
            shared_hosts=len(carrying),
            targets_total=len(scope.ids),
            truncated=len(carrying) > len(drawn),
        )

    async def _estate(self, scope: QueryScope) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Subdomain.id)).where(scope.match(Subdomain.scan_id))
            )
            or 0
        )


def _hub(hub: Hub, index: dict[UUID, int]) -> CorrelationHub | None:
    members = sorted(index[m.id] for m in hub.members if m.id in index)
    if not members:
        return None
    return CorrelationHub(
        id=hub.id,
        kind=hub.kind,
        value=hub.value,
        label=hub.label,
        count=hub.hosts,
        targets=hub.targets,
        share=round(hub.share, 4),
        common=hub.common,
        platform=bool(hub.platform),
        platform_label=hub.platform,
        query=hub.query,
        members=members,
    )


def _kinds(
    hubs: list[CorrelationHub],
    covered: dict[str, int],
    total: int,
    discovered: dict[str, int],
) -> list[CorrelationKindStat]:
    drawn: dict[str, list[CorrelationHub]] = {}
    for hub in hubs:
        drawn.setdefault(hub.kind, []).append(hub)
    return [
        CorrelationKindStat(
            key=kind,
            label=CORRELATION_KIND_LABELS[kind],
            help=CORRELATION_KIND_HELP[kind],
            default=kind in CORRELATION_DEFAULT_KINDS,
            hubs=len(drawn.get(kind, [])),
            total=discovered.get(kind, 0),
            common=sum(1 for h in drawn.get(kind, []) if h.common),
            platform=sum(1 for h in drawn.get(kind, []) if h.platform),
            crossing=sum(1 for h in drawn.get(kind, []) if h.targets > 1),
            hosts=covered.get(kind, 0),
        )
        for kind in CORRELATION_KIND_ORDER
        if total == 0 or drawn.get(kind)
    ]
