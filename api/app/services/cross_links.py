"""A value one target shares with another, once the provider's own identity is refused."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.surface_scope import SurfaceScopeService
from shared.definitions.correlation import (
    CORRELATION_KIND_LABELS,
    CROSS_COMMON_TARGET_SHARE,
    CROSS_LINK_ORDER,
    CROSS_PAGE_KINDS,
    MAX_CROSS_LINKS,
    MAX_CROSS_PEERS,
    MAX_CROSS_VALUES,
    MIN_BODY_BYTES,
    MIN_TARGETS_FOR_COMMON,
    CorrelationKind,
)
from shared.definitions.surface import SurfaceDimension
from shared.models.crosslink import CrossLink, CrossLinkPeer
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.services.asset_query.groups import group_token
from shared.services.asset_query.scope import QueryScope
from shared.utils.infra import generic_page, shared_edge
from shared.utils.net import cert_covers

MIN_TARGETS = 2

_TOKEN_OP: dict[str, str] = {CorrelationKind.IP.value: ":"}

_ASSET_COLUMNS = {
    CorrelationKind.BODY.value: HttpAsset.content_hash,
    CorrelationKind.CERT.value: HttpAsset.tls_fingerprint,
}

_HOST_COLUMNS = {
    CorrelationKind.TITLE.value: Subdomain.page_title,
    CorrelationKind.FAVICON.value: Subdomain.favicon_hash,
    CorrelationKind.CNAME.value: Subdomain.cname,
}


@dataclass(frozen=True)
class Carrier:
    host: str
    target_id: UUID
    cname: str | None = None
    status: int | None = None
    title: str | None = None
    subject_cn: str | None = None
    sans: tuple[str, ...] = ()

    def vouches(self, kind: str) -> bool:
        """Whether the identity this host presents is its own rather than a platform's."""
        if shared_edge(self.cname):
            return False
        if kind in CROSS_PAGE_KINDS:
            return generic_page(self.title, [self.status]) is None
        if kind == CorrelationKind.CERT.value:
            return cert_covers(self.host, self.subject_cn, self.sans)
        return True


class CrossLinkService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_rows(
        self, project_id: UUID, rows: list[Subdomain]
    ) -> dict[UUID, list[CrossLink]]:
        if not rows:
            return {}
        targets = await self._target_values(project_id)
        if len(targets) < MIN_TARGETS:
            return {}
        scope = await SurfaceScopeService(self.session).scope(
            project_id, SurfaceDimension.WEB_ASSETS.value
        )
        if not scope:
            return {}

        held = await self._asset_values(scope, [r.name for r in rows])
        carriers = await self._carriers(scope, self._wanted(rows), held)
        return self._assemble(rows, held, carriers, targets)

    async def _target_values(self, project_id: UUID) -> dict[UUID, str]:
        rows = await self.session.execute(
            select(Target.id, Target.target_value).where(
                Target.project_id == project_id
            )
        )
        return {row[0]: row[1] for row in rows.all()}

    def _wanted(self, rows: list[Subdomain]) -> dict[str, set[str]]:
        """The values on this page worth asking the estate about."""
        wanted: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            title = row.page_title
            if title and generic_page(title, [row.http_status]) is None:
                wanted[CorrelationKind.TITLE.value].add(title)
            if row.favicon_hash:
                wanted[CorrelationKind.FAVICON.value].add(row.favicon_hash)
            if row.cname and shared_edge(row.cname) is None:
                wanted[CorrelationKind.CNAME.value].add(row.cname)
            if not row.is_cdn:
                for ip in row.resolved_ips or []:
                    wanted[CorrelationKind.IP.value].add(ip)
        return {
            kind: set(sorted(values)[:MAX_CROSS_VALUES])
            for kind, values in wanted.items()
        }

    async def _asset_values(
        self, scope: QueryScope, hosts: list[str]
    ) -> dict[str, dict[str, str]]:
        """The identities the page's hosts present, read off their HTTP asset."""
        out: dict[str, dict[str, str]] = {kind: {} for kind in _ASSET_COLUMNS}
        if not hosts:
            return out
        rows = await self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.content_hash,
                HttpAsset.tls_fingerprint,
                HttpAsset.content_length,
            ).where(scope.match(HttpAsset.scan_id), HttpAsset.host.in_(hosts))
        )
        for host, body, cert, length in rows.all():
            if body and (length or 0) >= MIN_BODY_BYTES:
                out[CorrelationKind.BODY.value].setdefault(host, body)
            if cert:
                out[CorrelationKind.CERT.value].setdefault(host, cert)
        return out

    async def _carriers(
        self,
        scope: QueryScope,
        wanted: dict[str, set[str]],
        held: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, list[Carrier]]]:
        out: dict[str, dict[str, list[Carrier]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for kind, column in _HOST_COLUMNS.items():
            crossing = await self._crossing(scope, column, wanted.get(kind, set()))
            for value, carrier in await self._host_carriers(scope, column, crossing):
                out[kind][value].append(carrier)
        for value, carrier in await self._address_carriers(
            scope, wanted.get(CorrelationKind.IP.value, set())
        ):
            out[CorrelationKind.IP.value][value].append(carrier)
        for kind, column in _ASSET_COLUMNS.items():
            values = set(sorted(set(held.get(kind, {}).values()))[:MAX_CROSS_VALUES])
            for value, carrier in await self._asset_carriers(scope, column, values):
                out[kind][value].append(carrier)
        return out

    async def _crossing(self, scope: QueryScope, column, values: set[str]) -> set[str]:
        """The values more than one target carries."""
        if not values:
            return set()
        rows = await self.session.execute(
            select(column)
            .where(
                scope.match(Subdomain.scan_id),
                Subdomain.is_excluded.is_(False),
                column.in_(values),
            )
            .group_by(column)
            .having(func.count(func.distinct(Subdomain.target_id)) >= MIN_TARGETS)
        )
        return {row[0] for row in rows.all()}

    async def _host_carriers(
        self, scope: QueryScope, column, values: set[str]
    ) -> list[tuple[str, Carrier]]:
        if not values:
            return []
        rows = await self.session.execute(
            select(
                column,
                Subdomain.name,
                Subdomain.target_id,
                Subdomain.cname,
                Subdomain.http_status,
                Subdomain.page_title,
            ).where(
                scope.match(Subdomain.scan_id),
                Subdomain.is_excluded.is_(False),
                column.in_(values),
            )
        )
        return [
            (value, Carrier(name, target_id, cname, status, title))
            for value, name, target_id, cname, status, title in rows.all()
        ]

    async def _address_carriers(
        self, scope: QueryScope, values: set[str]
    ) -> list[tuple[str, Carrier]]:
        if not values:
            return []
        rows = await self.session.execute(
            select(
                Subdomain.resolved_ips,
                Subdomain.name,
                Subdomain.target_id,
                Subdomain.cname,
                Subdomain.http_status,
                Subdomain.page_title,
            ).where(
                scope.match(Subdomain.scan_id),
                Subdomain.is_excluded.is_(False),
                Subdomain.is_cdn.is_(False),
                func.jsonb_exists_any(
                    cast(Subdomain.resolved_ips, JSONB), pg_array(sorted(values))
                ),
            )
        )
        out: list[tuple[str, Carrier]] = []
        for ips, name, target_id, cname, status, title in rows.all():
            carrier = Carrier(name, target_id, cname, status, title)
            out.extend((ip, carrier) for ip in set(ips or []) & values)
        return out

    async def _asset_carriers(
        self, scope: QueryScope, column, values: set[str]
    ) -> list[tuple[str, Carrier]]:
        if not values:
            return []
        rows = await self.session.execute(
            select(
                column,
                HttpAsset.host,
                HttpAsset.target_id,
                HttpAsset.cname,
                HttpAsset.status_code,
                HttpAsset.title,
                HttpAsset.tls_subject_cn,
                HttpAsset.tls_sans,
            ).where(scope.match(HttpAsset.scan_id), column.in_(values))
        )
        seen: set[tuple[str, str]] = set()
        out: list[tuple[str, Carrier]] = []
        for value, host, target_id, cname, status, title, cn, sans in rows.all():
            if (value, host) in seen:
                continue
            seen.add((value, host))
            out.append(
                (
                    value,
                    Carrier(
                        host,
                        target_id,
                        cname,
                        status,
                        title,
                        cn,
                        tuple(str(x) for x in (sans or [])),
                    ),
                )
            )
        return out

    def _assemble(
        self,
        rows: list[Subdomain],
        held: dict[str, dict[str, str]],
        carriers: dict[str, dict[str, list[Carrier]]],
        targets: dict[UUID, str],
    ) -> dict[UUID, list[CrossLink]]:
        reach = (
            max(int(len(targets) * CROSS_COMMON_TARGET_SHARE), MIN_TARGETS)
            if len(targets) >= MIN_TARGETS_FOR_COMMON
            else len(targets)
        )
        shared = self._shared(carriers, reach)
        out: dict[UUID, list[CrossLink]] = {}
        for row in rows:
            links = [
                link
                for kind in CROSS_LINK_ORDER
                if (value := self._value_for(row, kind, held))
                and (link := self._link(row, kind, value, shared, targets))
            ]
            if links:
                out[row.id] = links[:MAX_CROSS_LINKS]
        return out

    def _shared(
        self, carriers: dict[str, dict[str, list[Carrier]]], reach: int
    ) -> dict[tuple[str, str], list[Carrier]]:
        """The vouching carriers of every value that crosses targets, judged once."""
        out: dict[tuple[str, str], list[Carrier]] = {}
        for kind, by_value in carriers.items():
            for value, found in by_value.items():
                if len({c.target_id for c in found}) < MIN_TARGETS:
                    continue
                held = [c for c in found if c.vouches(kind)]
                owners = {c.target_id for c in held}
                if not MIN_TARGETS <= len(owners) <= reach:
                    continue
                if kind == CorrelationKind.TITLE.value and generic_page(
                    value, [c.status for c in held]
                ):
                    continue
                out[(kind, value)] = held
        return out

    def _value_for(
        self, row: Subdomain, kind: str, held: dict[str, dict[str, str]]
    ) -> str | None:
        if kind in _ASSET_COLUMNS:
            return held.get(kind, {}).get(row.name)
        if kind == CorrelationKind.TITLE.value:
            return row.page_title
        if kind == CorrelationKind.FAVICON.value:
            return row.favicon_hash
        if kind == CorrelationKind.CNAME.value:
            return row.cname
        return None

    def _link(
        self,
        row: Subdomain,
        kind: str,
        value: str,
        shared: dict[tuple[str, str], list[Carrier]],
        targets: dict[UUID, str],
    ) -> CrossLink | None:
        held = shared.get((kind, value))
        if not held:
            return None
        if not any(c.target_id == row.target_id and c.host == row.name for c in held):
            return None
        peers = sorted(
            (c for c in held if c.target_id != row.target_id),
            key=lambda c: (targets.get(c.target_id, ""), c.host),
        )
        if not peers:
            return None
        return CrossLink(
            kind=kind,
            label=CORRELATION_KIND_LABELS[kind],
            value=value,
            query=group_token(kind, _TOKEN_OP.get(kind, "="), value),
            peers=[
                CrossLinkPeer(
                    host=c.host,
                    target_id=c.target_id,
                    target_value=targets.get(c.target_id, ""),
                )
                for c in peers[:MAX_CROSS_PEERS]
            ],
            targets=sorted({targets.get(c.target_id, "") for c in peers}),
            hosts=len(peers),
        )
