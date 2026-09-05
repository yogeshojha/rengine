"""What the shape of the discovered surface says, as findings rather than counts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, cast, desc, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import predicates as preds
from shared.definitions.endpoints import (
    CLASS_LABELS,
    INTEREST_LABELS,
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

_MIN_WALLED = 2
_MAX_OPEN_INSIDE = 2
_MIN_SHARED_HOSTS = 3
_TOP = 6
_AUTH_STATUS = (401, 403)
_CONTENT_CLASSES = (
    EndpointClass.IMAGE.value,
    EndpointClass.STYLE.value,
    EndpointClass.MEDIA.value,
    EndpointClass.OTHER.value,
)
_NEEDS_QUOTE = ' ()"[]:=><~'


def _token(field: str, value: str, op: str = ":") -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = (
        f'"{escaped}"' if any(c in value for c in _NEEDS_QUOTE) or not value else value
    )
    return f"{field}{op}{quoted}"


def _plural(word: str, n: int) -> str:
    return word if n == 1 else f"{word}s"


class EndpointStructureService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build(self, scan_id: UUID) -> ScanStructure:
        out = ScanStructure()
        totals = (
            await self.session.execute(
                select(
                    func.count().label("endpoints"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                    func.count(func.distinct(Endpoint.dir_path)).label("dirs"),
                    func.max(Endpoint.depth).label("depth"),
                    func.count().filter(Endpoint.is_probed.is_(True)).label("probed"),
                    func.count().filter(Endpoint.param_count > 0).label("params"),
                ).where(Endpoint.scan_id == scan_id)
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
        walled = func.count().filter(Endpoint.status_code.in_(_AUTH_STATUS))
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
                        walled >= _MIN_WALLED,
                        opened >= 1,
                        opened <= _MAX_OPEN_INSIDE,
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
                    f"{row.walled} {_plural('endpoint', row.walled)} in this folder "
                    f"{'requires' if row.walled == 1 else 'require'} authentication, but "
                    f"{row.opened} {'answers' if row.opened == 1 else 'answer'} without it."
                ),
                count=int(row.opened),
                query=(
                    f"{_token('dir', row.dir_path, '=')} "
                    f"{_token('host', row.host, '=')} status:200..299"
                ),
                samples=[row.sample] if row.sample else [],
            )
            for row in rows
        ]

    async def _exposed_files(self, scan_id: UUID) -> list[StructureFinding]:
        value = func.jsonb_array_elements_text(
            cast(Endpoint.interest, JSONB)
        ).column_valued("v")
        rows = (
            await self.session.execute(
                select(
                    value.label("interest"),
                    func.count(func.distinct(Endpoint.id)).label("n"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                    func.min(Endpoint.url).label("sample"),
                )
                .select_from(Endpoint)
                .where(
                    Endpoint.scan_id == scan_id,
                    value.in_(("vcs", "secrets", "backup")),
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
                    f"{row.n} {_plural('path', row.n)} across {row.hosts} "
                    f"{_plural('host', row.hosts)} match this pattern."
                ),
                count=int(row.n),
                query=_token("interest", row.interest),
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
                label="Known only to an archive",
                detail=(
                    f"{count} {_plural('endpoint', count)} were recorded by a public archive "
                    "and this scan could not reach them."
                ),
                count=count,
                query="is:archive-only",
            )
        ]

    async def _shared_paths(self, scan_id: UUID) -> list[PathSpread]:
        """The same route on many hosts is one framework, so one fix closes many findings."""
        hosts = func.count(func.distinct(Endpoint.host))
        rows = (
            await self.session.execute(
                select(
                    Endpoint.path,
                    hosts.label("hosts"),
                    func.count().label("endpoints"),
                )
                .where(
                    Endpoint.scan_id == scan_id,
                    Endpoint.path != "/",
                    Endpoint.endpoint_class.notin_(_CONTENT_CLASSES),
                )
                .group_by(Endpoint.path)
                .having(hosts >= _MIN_SHARED_HOSTS)
                .order_by(desc("hosts"), Endpoint.path)
                .limit(_TOP)
            )
        ).all()
        return [
            PathSpread(
                path=row.path,
                hosts=int(row.hosts),
                endpoints=int(row.endpoints),
                query=_token("path", row.path, "="),
            )
            for row in rows
        ]

    async def _interest(self, scan_id: UUID) -> list[StructureLine]:
        value = func.jsonb_array_elements_text(
            cast(Endpoint.interest, JSONB)
        ).column_valued("v")
        rows = (
            await self.session.execute(
                select(
                    value.label("interest"),
                    func.count(func.distinct(Endpoint.id)).label("n"),
                    func.count(func.distinct(Endpoint.host)).label("hosts"),
                )
                .select_from(Endpoint)
                .where(Endpoint.scan_id == scan_id)
                .group_by(value)
                .order_by(desc("n"))
                .limit(10)
            )
        ).all()
        return [
            StructureLine(
                key=row.interest,
                label=INTEREST_LABELS.get(row.interest, row.interest),
                count=int(row.n),
                hosts=int(row.hosts),
                query=_token("interest", row.interest),
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
                query=_token("class", key),
            )
            for key, n in rows
        ]

    async def _by_source(self, scan_id: UUID) -> list[StructureLine]:
        value = func.jsonb_array_elements_text(
            cast(Endpoint.sources, JSONB)
        ).column_valued("v")
        rows = (
            await self.session.execute(
                select(
                    value.label("source"),
                    func.count(func.distinct(Endpoint.id)).label("n"),
                )
                .select_from(Endpoint)
                .where(Endpoint.scan_id == scan_id)
                .group_by(value)
                .order_by(desc("n"))
            )
        ).all()
        return [
            StructureLine(
                key=row.source,
                label=SOURCE_LABELS.get(row.source, row.source),
                count=int(row.n),
                query=_token("source", row.source),
            )
            for row in rows
        ]


def _headline(out: ScanStructure) -> str:
    """The finding leads, never the total."""
    auth = [f for f in out.findings if f.kind == "auth_boundary"]
    if auth:
        n = len(auth)
        one = n == 1
        return (
            f"{n} {_plural('folder', n)} {'is' if one else 'are'} walled off but still "
            f"{'answers' if one else 'answer'} from inside"
        )
    exposed = [f for f in out.findings if f.kind == "exposed_file"]
    if exposed:
        total = sum(f.count for f in exposed)
        return f"{total} {_plural('path', total)} expose source, credentials or backups"
    if out.shared_paths:
        top = out.shared_paths[0]
        return f"{top.path} answers on {top.hosts} hosts"
    if out.with_params:
        return f"{out.with_params} {_plural('endpoint', out.with_params)} accept input"
    return f"{out.endpoints} endpoints across {out.hosts} {_plural('host', out.hosts)}"
