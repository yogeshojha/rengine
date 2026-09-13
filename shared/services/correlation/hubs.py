"""Shared identities over any scope: one scan, or every target's covering scan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import distinct, func, select, text

from shared.definitions.correlation import (
    COMMON_SHARE,
    CORRELATION_KIND_ORDER,
    CROSS_PAGE_KINDS,
    MAX_HUBS_PER_KIND,
    MIN_ESTATE_FOR_COMMON,
    MIN_SHARED,
    CorrelationKind,
)
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.subdomain import Subdomain
from shared.services.asset_query.errors import NO_JIT, STATEMENT_TIMEOUT
from shared.services.asset_query.renders import cluster, is_identity
from shared.services.asset_query.tokens import group_token
from shared.services.correlation.kinds import KINDS, asset_join, platform_for
from shared.utils.imagehash import hex_digest
from shared.utils.infra import generic_page, shared_edge

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.services.asset_query.scope import QueryScope

_LABEL_MAX = 60
_HASH_LABEL = 14
# loaded past the cut, then re-ranked once the provider test has run
_PLATFORM_SLACK = 40
_MEMBER_COLUMNS = (
    Subdomain.id,
    Subdomain.name,
    Subdomain.target_id,
    Subdomain.http_status,
    Subdomain.is_active,
    Subdomain.page_title,
    Subdomain.cname,
)
_HASH_KINDS = frozenset(
    {
        CorrelationKind.BODY.value,
        CorrelationKind.JARM.value,
        CorrelationKind.FAVICON.value,
        CorrelationKind.SCREENSHOT.value,
        CorrelationKind.HEADERS.value,
    }
)


def _member(row) -> Member:
    identifier, name, target_id, status, active, title, cname = row
    return Member(identifier, name, target_id, status, bool(active), title, cname)


def hub_label(kind: str, value: str) -> str:
    if kind == CorrelationKind.ASN.value:
        return f"AS{value}"
    if kind in _HASH_KINDS:
        return value if len(value) <= _HASH_LABEL else f"{value[:8]}…{value[-4:]}"
    return value if len(value) <= _LABEL_MAX else f"{value[: _LABEL_MAX - 1]}…"


@dataclass(frozen=True)
class Member:
    """One row carrying a hub's value."""

    id: UUID
    name: str
    target_id: UUID
    status: int | None
    active: bool
    title: str | None
    cname: str | None = None

    def vouches(self, kind: str) -> bool:
        """Whether the identity this row presents is its own rather than a provider's."""
        if shared_edge(self.cname):
            return False
        if kind in CROSS_PAGE_KINDS:
            return generic_page(self.title, [self.status]) is None
        return True


@dataclass
class Hub:
    """One shared identity, counted over the whole scope."""

    kind: str
    value: str
    hosts: int
    targets: int
    carriers: int
    platform: str = ""
    members: list[Member] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.value}"

    @property
    def label(self) -> str:
        return hub_label(self.kind, self.value)

    @property
    def share(self) -> float:
        return self.hosts / self.carriers if self.carriers else 0.0

    @property
    def common(self) -> bool:
        return self.carriers >= MIN_ESTATE_FOR_COMMON and self.share >= COMMON_SHARE

    @property
    def query(self) -> str:
        spec = KINDS[self.kind]
        return group_token(spec.kind, spec.operator, self.value) + spec.narrows


@dataclass
class HubSet:
    hubs: list[Hub] = field(default_factory=list)
    carriers: dict[str, int] = field(default_factory=dict)
    discovered: dict[str, int] = field(default_factory=dict)

    def by_kind(self, kind: str) -> list[Hub]:
        return [h for h in self.hubs if h.kind == kind]

    def holding(self, subdomain_id: UUID) -> list[Hub]:
        return [h for h in self.hubs if any(m.id == subdomain_id for m in h.members)]


class CorrelationFinder:
    """Hub discovery in SQL, over every row in scope."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find(
        self,
        scope: QueryScope,
        *,
        kinds: tuple[str, ...] = CORRELATION_KIND_ORDER,
        per_kind: int = MAX_HUBS_PER_KIND,
        values: dict[str, set[str]] | None = None,
    ) -> HubSet:
        if not scope:
            return HubSet()
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        addresses = await self._cdn_addresses(scope)
        cross = len(scope.ids) > 1
        out = HubSet()
        for kind in kinds:
            spec = KINDS.get(kind)
            if spec is None:
                continue
            wanted = values.get(kind) if values is not None else None
            if values is not None and not wanted:
                continue
            if spec.derived:
                hubs, carriers = await self._render_hubs(scope, wanted)
            else:
                hubs, carriers = await self._column_hubs(scope, kind, wanted)
            out.carriers[kind] = carriers
            out.discovered[kind] = len(hubs)
            for hub in hubs:
                hub.platform = platform_for(kind, hub.value, addresses)
            hubs.sort(key=lambda h: self._rank(h, cross))
            kept = hubs[: per_kind + _PLATFORM_SLACK]
            if kept:
                await self._load_members(scope, kind, kept)
                for hub in kept:
                    hub.platform = hub.platform or _written_by(hub)
                kept.sort(key=lambda h: self._rank(h, cross))
                kept = kept[:per_kind]
            out.hubs.extend(kept)
        return out

    @staticmethod
    def _rank(hub: Hub, cross: bool) -> tuple:
        """Least explained first, and across targets before inside one."""
        head = (bool(hub.platform), hub.common)
        return (
            (*head, -hub.targets, -hub.hosts, hub.value)
            if cross
            else (
                *head,
                -hub.hosts,
                hub.value,
            )
        )

    async def _column_hubs(
        self, scope: QueryScope, kind: str, wanted: set[str] | None
    ) -> tuple[list[Hub], int]:
        spec = KINDS[kind]
        value = spec.value().label("value")
        base = (
            select(
                value,
                func.count(distinct(Subdomain.id)).label("hosts"),
                func.count(distinct(Subdomain.target_id)).label("targets"),
            )
            .select_from(Subdomain)
            .where(scope.match(Subdomain.scan_id), value.isnot(None))
        )
        if spec.asset:
            base = base.join(HttpAsset, asset_join())
        if not spec.numeric:
            base = base.where(value != "")
        for condition in spec.conditions():
            base = base.where(condition)
        if wanted is not None:
            base = base.where(value.in_([spec.bind(v) for v in sorted(wanted)]))
        grouped = base.group_by(value).subquery()
        rows = (
            await self.session.execute(
                select(grouped).where(grouped.c.hosts >= MIN_SHARED)
            )
        ).all()
        carriers = await self._carriers(scope, kind) if rows else 0
        return [
            Hub(
                kind=kind,
                value=str(row.value),
                hosts=int(row.hosts),
                targets=int(row.targets),
                carriers=carriers,
            )
            for row in rows
        ], carriers

    async def _carriers(self, scope: QueryScope, kind: str) -> int:
        """Every host in scope carrying this kind, whatever value it carries."""
        spec = KINDS[kind]
        value = spec.value()
        stmt = (
            select(func.count(distinct(Subdomain.id)))
            .select_from(Subdomain)
            .where(scope.match(Subdomain.scan_id), value.isnot(None))
        )
        if spec.asset:
            stmt = stmt.join(HttpAsset, asset_join())
        if not spec.numeric:
            stmt = stmt.where(value != "")
        for condition in spec.conditions():
            stmt = stmt.where(condition)
        return int(await self.session.scalar(stmt) or 0)

    async def _render_hubs(
        self, scope: QueryScope, wanted: set[str] | None
    ) -> tuple[list[Hub], int]:
        """Screenshot balls, counted the way `screenshot:` filters."""
        rows = (
            await self.session.execute(
                select(
                    Subdomain.screenshot_phash,
                    func.count(),
                    func.count(distinct(Subdomain.target_id)),
                )
                .where(
                    scope.match(Subdomain.scan_id),
                    Subdomain.screenshot_phash.isnot(None),
                )
                .group_by(Subdomain.screenshot_phash)
            )
        ).all()
        histogram = {int(raw): int(n) for raw, n, _ in rows}
        targets = {int(raw): int(t) for raw, _, t in rows}
        carriers = sum(n for h, n in histogram.items() if is_identity(h))
        hubs = []
        for found in cluster(histogram):
            if found.count < MIN_SHARED:
                continue
            digest = found.digest
            if wanted is not None and not any(
                hex_digest(h) in wanted for h in found.hashes
            ):
                continue
            hubs.append(
                Hub(
                    kind=CorrelationKind.SCREENSHOT.value,
                    value=digest,
                    hosts=found.count,
                    targets=max(targets.get(h, 0) for h in found.hashes),
                    carriers=carriers,
                )
            )
        return hubs, carriers

    async def _load_members(
        self, scope: QueryScope, kind: str, hubs: list[Hub]
    ) -> None:
        spec = KINDS[kind]
        by_value = {hub.value: hub for hub in hubs}
        if spec.derived:
            pairs = await self._render_members(scope, set(by_value))
        else:
            value = spec.value().label("value")
            stmt = (
                select(value, *_MEMBER_COLUMNS)
                .select_from(Subdomain)
                .where(
                    scope.match(Subdomain.scan_id),
                    value.in_([spec.bind(v) for v in sorted(by_value)]),
                )
            )
            if spec.asset:
                stmt = stmt.join(HttpAsset, asset_join())
            for condition in spec.conditions():
                stmt = stmt.where(condition)
            pairs = [
                (str(row[0]), _member(row[1:]))
                for row in (await self.session.execute(stmt)).all()
            ]
        seen: set[tuple[str, UUID]] = set()
        for key, member in pairs:
            hub = by_value.get(key)
            if hub is None or (key, member.id) in seen:
                continue
            seen.add((key, member.id))
            hub.members.append(member)

    async def _render_members(
        self, scope: QueryScope, drawn: set[str]
    ) -> list[tuple[str, Member]]:
        digests: dict[int, str] = {}
        for found in cluster(await self._render_histogram(scope)):
            if found.digest in drawn:
                for raw in found.hashes:
                    digests.setdefault(raw, found.digest)
        if not digests:
            return []
        rows = (
            await self.session.execute(
                select(Subdomain.screenshot_phash, *_MEMBER_COLUMNS).where(
                    scope.match(Subdomain.scan_id),
                    Subdomain.screenshot_phash.in_(sorted(digests)),
                )
            )
        ).all()
        return [(digests[int(row[0])], _member(row[1:])) for row in rows]

    async def _render_histogram(self, scope: QueryScope) -> dict[int, int]:
        rows = (
            await self.session.execute(
                select(Subdomain.screenshot_phash, func.count())
                .where(
                    scope.match(Subdomain.scan_id),
                    Subdomain.screenshot_phash.isnot(None),
                )
                .group_by(Subdomain.screenshot_phash)
            )
        ).all()
        return {int(raw): int(n) for raw, n in rows}

    async def _cdn_addresses(self, scope: QueryScope) -> dict[str, str]:
        rows = (
            await self.session.execute(
                select(IpAddress.ip, IpAddress.cdn_name).where(
                    scope.match(IpAddress.scan_id), IpAddress.is_cdn.is_(True)
                )
            )
        ).all()
        return {ip: name or "CDN" for ip, name in rows}


def _written_by(hub: Hub) -> str:
    """The provider that wrote this value, when nothing carrying it speaks for itself."""
    held = [m for m in hub.members if m.vouches(hub.kind)]
    if hub.kind == CorrelationKind.TITLE.value:
        return generic_page(hub.value, [m.status for m in held]) or ""
    if not hub.members or held:
        return ""
    if hub.kind in CROSS_PAGE_KINDS:
        return generic_page(hub.members[0].title, [hub.members[0].status]) or ""
    return shared_edge(hub.members[0].cname) or ""
