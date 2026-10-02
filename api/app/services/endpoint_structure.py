"""Findings read from the shape of the discovered surface."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, cast, desc, func, select, true
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.endpoint_tree import MAX_OPEN_INSIDE, MIN_WALLED
from shared.definitions.endpoints import (
    CLASS_LABELS,
    INTEREST_LABELS,
    SENSITIVE_INTERESTS,
    SOURCE_LABELS,
    EndpointClass,
)
from shared.models.endpoint import (
    Endpoint,
    PathSpread,
    ScanStructure,
    StructureFinding,
    StructureLine,
)
from shared.services.asset_query import array_elements, element_counts
from shared.services.asset_query import predicates as preds
from shared.services.asset_query.tokens import token as _token
from shared.utils.text import plural

_MIN_SHARED_HOSTS = 3
_TOP = 6
_CONTENT_CLASSES = (
    EndpointClass.IMAGE.value,
    EndpointClass.STYLE.value,
    EndpointClass.MEDIA.value,
    EndpointClass.OTHER.value,
)
_TOP_INTEREST = 10


class EndpointStructureService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build(self, scan_id: UUID) -> ScanStructure:
        out = ScanStructure()
        folders = (
            select(
                Endpoint.host,
                Endpoint.dir_path,
                func.count().label("n"),
                func.max(Endpoint.depth).label("depth"),
                func.count().filter(Endpoint.is_probed.is_(True)).label("probed"),
                func.count().filter(Endpoint.param_count > 0).label("params"),
            )
            .where(Endpoint.scan_id == scan_id)
            .group_by(Endpoint.host, Endpoint.dir_path)
            .subquery()
        )
        totals = (
            await self.session.execute(
                select(
                    func.sum(folders.c.n).label("endpoints"),
                    func.count(func.distinct(folders.c.host)).label("hosts"),
                    func.count(func.distinct(folders.c.dir_path)).label("dirs"),
                    func.max(folders.c.depth).label("depth"),
                    func.sum(folders.c.probed).label("probed"),
                    func.sum(folders.c.params).label("params"),
                )
            )
        ).one()
        out.endpoints = int(totals.endpoints or 0)
        if not out.endpoints:
            return out
        out.hosts = int(totals.hosts or 0)
        out.directories = int(totals.dirs or 0)
        out.max_depth = int(totals.depth or 0)
        out.probed = int(totals.probed or 0)
        out.with_params = int(totals.params or 0)

        out.findings = [
            *await self._auth_boundaries(scan_id),
            *await self._exposed_files(scan_id),
            *await self._archive_only(scan_id),
        ]
        out.shared_paths = await self._shared_paths(scan_id)
        out.interest = await self._interest(scan_id)
        out.by_class = await self._by_class(scan_id)
        out.by_source = await self._by_source(scan_id)
        out.headline = _headline(out)
        return out

    async def _auth_boundaries(self, scan_id: UUID) -> list[StructureFinding]:
        """A directory that is mostly walled off, with something answering inside it."""
        walled = func.count().filter(Endpoint.status_code.in_(preds.AUTH_STATUS))
        opened = func.count().filter(preds.endpoint_status_class("2xx"))
        rows = (
            await self.session.execute(
                select(
                    Endpoint.host,
                    Endpoint.dir_path,
                    walled.label("walled"),
                    opened.label("opened"),
                    func.min(Endpoint.url).label("sample"),
                )
                .where(Endpoint.scan_id == scan_id, Endpoint.is_probed.is_(True))
                .group_by(Endpoint.host, Endpoint.dir_path)
                .having(
                    and_(
                        walled >= MIN_WALLED,
                        opened >= 1,
                        opened <= MAX_OPEN_INSIDE,
                    )
                )
                .order_by(desc("walled"))
                .limit(_TOP)
            )
        ).all()
        return [
            StructureFinding(
                kind="auth_boundary",
                label=f"{row.dir_path} on {row.host}",
                detail=(
                    f"{row.walled} {plural(row.walled, 'endpoint')} "
                    f"{'requires' if row.walled == 1 else 'require'} authentication. "
                    f"{row.opened} {'answers' if row.opened == 1 else 'answer'} without it."
                ),
                count=int(row.opened),
                query=(
                    f"{_token('dir', '=', row.dir_path)} "
                    f"{_token('host', '=', row.host)} status:200..299"
                ),
                samples=[row.sample] if row.sample else [],
            )
            for row in rows
        ]

    async def _exposed_files(self, scan_id: UUID) -> list[StructureFinding]:
        sensitive = sorted(SENSITIVE_INTERESTS)
        element = array_elements(Endpoint.interest, "v")
        value = element.c.value
        rows = (
            await self.session.execute(
                select(
                    value.label("interest"),
                    func.count(func.distinct(Endpoint.id)).label("n"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                    func.min(Endpoint.url).label("sample"),
                )
                .select_from(Endpoint)
                .join(element, true())
                .where(
                    Endpoint.scan_id == scan_id,
                    cast(Endpoint.interest, JSONB).op("?|")(array(sensitive)),
                    value.in_(tuple(sensitive)),
                )
                .group_by(value)
                .order_by(desc("n"))
            )
        ).all()
        return [
            StructureFinding(
                kind="exposed_file",
                label=INTEREST_LABELS.get(row.interest, row.interest),
                detail=(
                    f"{row.n} {plural(row.n, 'path')} across {row.hosts} "
                    f"{plural(row.hosts, 'host')}."
                ),
                count=int(row.n),
                query=_token("interest", ":", row.interest),
                samples=[row.sample] if row.sample else [],
            )
            for row in rows
        ]

    async def _archive_only(self, scan_id: UUID) -> list[StructureFinding]:
        n = await self.session.scalar(
            select(func.count()).where(
                Endpoint.scan_id == scan_id, preds.endpoint_archive_only()
            )
        )
        count = int(n or 0)
        if not count:
            return []
        return [
            StructureFinding(
                kind="archive_only",
                label="Archive only",
                detail=(
                    f"{count} {plural(count, 'endpoint')} from a public archive "
                    "did not answer."
                ),
                count=count,
                query="is:archive-only",
            )
        ]

    async def _shared_paths(self, scan_id: UUID) -> list[PathSpread]:
        """Routes that answer on several hosts."""
        per_host = (
            select(Endpoint.path, Endpoint.host, func.count().label("n"))
            .where(
                Endpoint.scan_id == scan_id,
                Endpoint.path != "/",
                Endpoint.endpoint_class.notin_(_CONTENT_CLASSES),
            )
            .group_by(Endpoint.path, Endpoint.host)
            .subquery()
        )
        hosts = func.count(per_host.c.host)
        rows = (
            await self.session.execute(
                select(
                    per_host.c.path,
                    hosts.label("hosts"),
                    func.sum(per_host.c.n).label("endpoints"),
                )
                .group_by(per_host.c.path)
                .having(hosts >= _MIN_SHARED_HOSTS)
                .order_by(desc("hosts"), per_host.c.path)
                .limit(_TOP)
            )
        ).all()
        return [
            PathSpread(
                path=row.path,
                hosts=int(row.hosts),
                endpoints=int(row.endpoints),
                query=_token("path", "=", row.path),
            )
            for row in rows
        ]

    async def _interest(self, scan_id: UUID) -> list[StructureLine]:
        per_host = element_counts(
            select(Endpoint.id).where(Endpoint.scan_id == scan_id),
            Endpoint.interest,
            Endpoint.host,
        ).subquery()
        rows = (
            await self.session.execute(
                select(
                    per_host.c.value.label("interest"),
                    func.sum(per_host.c.n).label("n"),
                    func.count().label("hosts"),
                )
                .group_by(per_host.c.value)
                .order_by(desc("n"), per_host.c.value)
                .limit(_TOP_INTEREST)
            )
        ).all()
        return [
            StructureLine(
                key=row.interest,
                label=INTEREST_LABELS.get(row.interest, row.interest),
                count=int(row.n),
                hosts=int(row.hosts),
                query=_token("interest", ":", row.interest),
            )
            for row in rows
        ]

    async def _by_class(self, scan_id: UUID) -> list[StructureLine]:
        rows = (
            await self.session.execute(
                select(Endpoint.endpoint_class, func.count().label("n"))
                .where(Endpoint.scan_id == scan_id)
                .group_by(Endpoint.endpoint_class)
                .order_by(desc("n"))
            )
        ).all()
        return [
            StructureLine(
                key=key,
                label=CLASS_LABELS.get(key, key),
                count=int(n),
                query=_token("class", ":", key),
            )
            for key, n in rows
        ]

    async def _by_source(self, scan_id: UUID) -> list[StructureLine]:
        counted = element_counts(
            select(Endpoint.id).where(Endpoint.scan_id == scan_id), Endpoint.sources
        ).subquery()
        rows = (
            await self.session.execute(
                select(counted.c.value.label("source"), counted.c.n).order_by(
                    desc(counted.c.n)
                )
            )
        ).all()
        return [
            StructureLine(
                key=row.source,
                label=SOURCE_LABELS.get(row.source, row.source),
                count=int(row.n),
                query=_token("source", ":", row.source),
            )
            for row in rows
        ]


def _headline(out: ScanStructure) -> str:
    """The finding leads."""
    auth = [f for f in out.findings if f.kind == "auth_boundary"]
    if auth:
        n = len(auth)
        one = n == 1
        return (
            f"{n} {plural(n, 'folder')} behind authentication "
            f"{'answers' if one else 'answer'} on some paths"
        )
    exposed = [f for f in out.findings if f.kind == "exposed_file"]
    if exposed:
        total = sum(f.count for f in exposed)
        verb = plural(total, "exposes", "expose")
        return f"{total} {plural(total, 'path')} {verb} source, credentials or backups"
    if out.shared_paths:
        top = out.shared_paths[0]
        return f"{top.path} answers on {top.hosts} {plural(top.hosts, 'web asset')}"
    if out.with_params:
        verb = plural(out.with_params, "accepts", "accept")
        return f"{out.with_params} {plural(out.with_params, 'endpoint')} {verb} input"
    return (
        f"{out.endpoints} {plural(out.endpoints, 'endpoint')} "
        f"across {out.hosts} {plural(out.hosts, 'web asset')}"
    )
