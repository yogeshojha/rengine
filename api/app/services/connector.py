"""Connector registration, traffic ingest and queue-to-scan dispatch."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import cast, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB, array, insert
from sqlalchemy.ext.asyncio import AsyncSession

from connectors import auth
from connectors.ingest import Prepared, prepare
from connectors.notice import notices_for
from connectors.registry import connector as connector_for
from connectors.registry import connectors as all_connectors
from shared.definitions.bounty_programs import ScopeState
from shared.definitions.connectors import (
    ACTION_TTL_MINUTES,
    INGESTED_TOOLS,
    LOUD_NOTICES,
    MANUAL_RUN_LABEL,
    MAX_ACTION_BATCH,
    MAX_CANDIDATE_SCAN,
    MAX_CONNECTORS,
    MAX_NOTICE_BATCH,
    MAX_PENDING_ACTIONS,
    MAX_PICKER_TARGETS,
    MAX_QUEUE,
    MAX_SCOPE_HOSTS,
    NOTICE_LABELS,
    NOTICE_ORDER,
    SAFE_METHODS,
    ActionKind,
    CandidateState,
    ConnectorKind,
    SyncTrigger,
    state_for,
)
from shared.definitions.domains import (
    IGNORED_DOMAINS,
    PRIVATE_TLDS,
    RELATED_REASON_DETAIL,
    RELATED_REASON_LABELS,
    RelatedReason,
    registrable_domain,
)
from shared.definitions.endpoints import parse_url
from shared.definitions.rescan import SeedKind, stages_for
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import Protocol, Scanner, Severity
from shared.enums.scan import ScanScope, ScanStatus
from shared.models.bounty_program import BountyProgram, BountyScope
from shared.models.connector import (
    ActionRead,
    CandidatePage,
    CandidateRead,
    Connector,
    ConnectorAction,
    ConnectorCandidate,
    ConnectorCoverage,
    ConnectorCreate,
    ConnectorCreated,
    ConnectorHost,
    ConnectorRead,
    ConnectorScope,
    ConnectorSession,
    ConnectorUpdate,
    DiscoveredDomain,
    FindingRecorded,
    FindingReport,
    HostFacts,
    IngestRequest,
    IngestResult,
    NoticeRead,
    SessionRead,
    TargetAdded,
    TargetOption,
)
from shared.models.endpoint import Endpoint
from shared.models.scan import Scan, ScanCreate, SeedAsset
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control
from tools.nuclei.parser import fingerprint

_DIMENSION = SurfaceDimension.ENDPOINTS.value
PAGE_SIZE = 50
_RANK = (
    cast(ConnectorCandidate.notices, JSONB).has_any(array(tuple(LOUD_NOTICES))).desc(),
    ConnectorCandidate.target_id.is_not(None).desc(),
    ConnectorCandidate.param_count.desc(),
    ConnectorCandidate.last_seen_at.desc(),
)
SESSION_GAP_MINUTES = 15
MAX_SESSIONS = 40
MAX_DISCOVERED = 40
MAX_DISCOVERED_HOSTNAMES = 12


class ConnectorError(RuntimeError):
    """The connector configuration is not valid."""


def _guard(exc: ConnectorError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _as_url(host: str) -> str:
    """A proxy's scope is expressed as URLs, not bare hostnames."""
    value = host.strip()
    return value if value.startswith(("http://", "https://")) else f"https://{value}"


def _host_matches(host: str, value: str) -> bool:
    value = value.lower().strip().rstrip(".")
    return bool(value) and (host == value or host.endswith(f".{value}"))


class ConnectorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # registration ---------------------------------------------------------

    def catalog(self) -> list[dict]:
        return [c.spec() for c in all_connectors().values()]

    async def list(self, project_id: uuid.UUID) -> list[ConnectorRead]:
        rows = (
            (
                await self.session.execute(
                    select(Connector)
                    .where(Connector.project_id == project_id)
                    .order_by(Connector.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        owned = await self._owned_domains(project_id)
        return [await self._read(row, owned=owned) for row in rows]

    async def get(self, connector_id: uuid.UUID, project_id: uuid.UUID) -> Connector:
        row = await self.session.get(Connector, connector_id)
        if row is None or row.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found."
            )
        return row

    async def create(
        self, data: ConnectorCreate, created_by: uuid.UUID, base_url: str = ""
    ) -> ConnectorCreated:
        if connector_for(data.kind) is None:
            msg = f"Unknown connector {data.kind!r}."
            raise ConnectorError(msg)
        count = await self.session.scalar(
            select(func.count())
            .select_from(Connector)
            .where(Connector.project_id == data.project_id)
        )
        if (count or 0) >= MAX_CONNECTORS:
            msg = f"This project already has {MAX_CONNECTORS} connectors."
            raise ConnectorError(msg)
        secret, token_hash, prefix = auth.mint()
        row = Connector(
            project_id=data.project_id,
            kind=data.kind,
            name=data.name.strip(),
            token_hash=token_hash,
            token_prefix=prefix,
            only_known_hosts=data.only_known_hosts,
            sync_trigger=data.sync_trigger,
            quiet_minutes=data.quiet_minutes,
            queue_threshold=data.queue_threshold,
            ingest_tools=[t for t in data.ingest_tools if t in INGESTED_TOOLS]
            or sorted(INGESTED_TOOLS),
            capture_bodies=data.capture_bodies,
            capture_sessions=data.capture_sessions,
            record_hosts=data.record_hosts,
            include_static=data.include_static,
            scan_safe_methods_only=data.scan_safe_methods_only,
            context_id=data.context_id,
            created_by=created_by,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return ConnectorCreated(
            connector=await self._read(row),
            secret=secret,
            setup=self._setup(row, secret, base_url),
        )

    async def update(
        self, connector_id: uuid.UUID, project_id: uuid.UUID, data: ConnectorUpdate
    ) -> ConnectorRead:
        row = await self.get(connector_id, project_id)
        fields = data.model_dump(exclude_unset=True)
        if "ingest_tools" in fields and fields["ingest_tools"] is not None:
            fields["ingest_tools"] = [
                t for t in fields["ingest_tools"] if t in INGESTED_TOOLS
            ] or sorted(INGESTED_TOOLS)
        for key, value in fields.items():
            if value is not None or key in {"target_id", "context_id"}:
                setattr(row, key, value)
        row.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(row)
        return await self._read(row)

    async def rotate(
        self, connector_id: uuid.UUID, project_id: uuid.UUID, base_url: str = ""
    ) -> ConnectorCreated:
        row = await self.get(connector_id, project_id)
        secret, token_hash, prefix = auth.mint()
        row.token_hash, row.token_prefix, row.updated_at = token_hash, prefix, utc_now()
        await self.session.commit()
        await self.session.refresh(row)
        return ConnectorCreated(
            connector=await self._read(row),
            secret=secret,
            setup=self._setup(row, secret, base_url),
        )

    async def delete(self, connector_id: uuid.UUID, project_id: uuid.UUID) -> None:
        row = await self.get(connector_id, project_id)
        await self.session.delete(row)
        await self.session.commit()

    async def authenticate(self, secret: str | None) -> Connector | None:
        if not secret or not auth.looks_like_token(secret):
            return None
        return await self.session.scalar(
            select(Connector).where(Connector.token_hash == auth.fingerprint(secret))
        )

    # ingest ---------------------------------------------------------------

    async def ingest(self, row: Connector, payload: IngestRequest) -> IngestResult:
        now = utc_now()
        if row.paused:
            return IngestResult(
                accepted=0,
                novel=0,
                dropped=len(payload.items),
                queued=0,
                flagged=[],
                ready=False,
            )
        batch = prepare(
            payload.items,
            include_static=row.include_static,
            ingest_tools=list(row.ingest_tools or []),
        )
        targets = await self._targets_all(row.project_id)
        if payload.program_id:
            targets = await self._program_targets(payload.program_id, row.project_id)
        chosen = await self._chosen_target(payload.target_id, row.project_id)
        forbidden = await self.forbidden_hosts(row.project_id)
        kept: list[tuple[Prepared, uuid.UUID | None]] = []
        dropped = batch.rejected
        for item in batch.prepared:
            target_id = chosen or self._resolve_target(item.parsed.host, targets)
            if target_id is None and row.only_known_hosts:
                dropped += 1
                continue
            kept.append((item, target_id))

        known = await self._known_signatures(
            row.project_id, [i.signature for i, _ in kept]
        )
        rows = [
            self._candidate_row(
                row,
                item,
                target_id,
                item.signature in known,
                now,
                self._forbidden(item.parsed.host, forbidden) is not None,
            )
            for item, target_id in kept
        ]
        flagged = [
            {
                "url": data["url"],
                "notices": data["notices"],
                "status_code": data["status_code"],
            }
            for data in rows
            if set(data["notices"]) & LOUD_NOTICES
        ][:20]
        novel = await self._upsert(rows) if rows else 0

        row.requests_seen += batch.seen
        row.dropped_out_of_scope += dropped
        row.last_seen_at = now
        client = strip_control(payload.client or "") if payload.client else ""
        row.last_client = (client or row.last_client or "")[:120] or None
        if row.record_hosts:
            await self._record_hosts(row, batch.hosts_seen, targets, now)
        kept_hosts = {item.parsed.host for item, _ in kept}
        if kept_hosts:
            await self._touch_session(
                row, payload.client, kept_hosts, batch.seen, novel, now
            )
        row.candidates = await self._count(row.id)
        await self.session.commit()

        queued = await self._count(row.id, states=(CandidateState.NEW.value,))
        return IngestResult(
            accepted=len(kept),
            novel=novel,
            dropped=dropped,
            queued=queued,
            flagged=flagged,
            ready=self._ready(row, queued, now),
        )

    def _candidate_row(
        self,
        row: Connector,
        item: Prepared,
        target_id: uuid.UUID | None,
        known: bool,
        now,
        out_of_scope: bool = False,
    ) -> dict:
        parsed = item.parsed
        return {
            "id": uuid.uuid4(),
            "connector_id": row.id,
            "project_id": row.project_id,
            "target_id": target_id,
            "signature": item.signature,
            "url": parsed.url,
            "scheme": parsed.scheme,
            "host": parsed.host,
            "port": parsed.port,
            "path": item.shape,
            "dir_path": parsed.dir_path,
            "filename": parsed.filename,
            "extension": parsed.extension,
            "depth": parsed.depth,
            "methods": item.methods,
            "params": list(item.params),
            "param_count": len(item.params),
            "endpoint_class": item.endpoint_class,
            "interests": item.interests,
            "notices": notices_for(
                interests=item.interests,
                methods=item.methods,
                status_code=item.status_code,
                known=known,
                in_scope=target_id is not None,
                out_of_scope=out_of_scope,
            ),
            "status_code": item.status_code,
            "content_type": item.content_type,
            "content_length": item.content_length,
            "title": item.title,
            "authenticated": item.authenticated,
            "source_tool": item.source_tool,
            "request_sample": item.request_sample if row.capture_bodies else None,
            "known": known,
            "state": CandidateState.NEW.value,
            "hits": item.hits,
            "first_seen_at": item.observed_at or now,
            "last_seen_at": item.observed_at or now,
        }

    async def _upsert(self, rows: list[dict]) -> int:
        """A shape already seen only moves forward."""
        rows.sort(key=lambda r: r["signature"])
        before = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(ConnectorCandidate.connector_id == rows[0]["connector_id"])
        )
        stmt = insert(ConnectorCandidate).values(rows)
        await self.session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_connector_candidate_signature",
                set_={
                    "hits": ConnectorCandidate.hits + stmt.excluded.hits,
                    "last_seen_at": stmt.excluded.last_seen_at,
                    "methods": stmt.excluded.methods,
                    "status_code": stmt.excluded.status_code,
                    "content_type": stmt.excluded.content_type,
                    "title": stmt.excluded.title,
                    "notices": stmt.excluded.notices,
                    "known": stmt.excluded.known,
                    "authenticated": ConnectorCandidate.authenticated
                    | stmt.excluded.authenticated,
                },
            )
        )
        await self.session.flush()
        after = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(ConnectorCandidate.connector_id == rows[0]["connector_id"])
        )
        return max((after or 0) - (before or 0), 0)

    async def _record_hosts(
        self, row: Connector, counts: dict[str, int], targets, now
    ) -> None:
        """The hostname ledger."""
        if not counts:
            return
        rows = [
            {
                "id": uuid.uuid4(),
                "connector_id": row.id,
                "project_id": row.project_id,
                "host": host,
                "registrable": registrable_domain(host),
                "target_id": self._resolve_target(host, targets),
                "requests": hits,
                "dismissed": False,
                "first_seen_at": now,
                "last_seen_at": now,
            }
            for host, hits in sorted(counts.items())
        ]
        stmt = insert(ConnectorHost).values(rows)
        await self.session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_connector_host",
                set_={
                    "requests": ConnectorHost.requests + stmt.excluded.requests,
                    "last_seen_at": stmt.excluded.last_seen_at,
                    "target_id": stmt.excluded.target_id,
                },
            )
        )

    async def _owned_domains(self, project_id: uuid.UUID) -> set[str]:
        return {
            registrable_domain(value)
            for _, value in await self._targets_all(project_id)
            if registrable_domain(value)
        }

    async def discovered(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        owned: set[str] | None = None,
    ) -> list[DiscoveredDomain]:
        """Domains this proxy reached that no target covers, vendors and noise removed."""
        await self.get(connector_id, project_id)
        if owned is None:
            owned = await self._owned_domains(project_id)
        hosts = (
            (
                await self.session.execute(
                    select(ConnectorHost).where(
                        ConnectorHost.connector_id == connector_id,
                        ConnectorHost.target_id.is_(None),
                        ConnectorHost.dismissed.is_(False),
                        ConnectorHost.registrable != "",
                    )
                )
            )
            .scalars()
            .all()
        )
        forbidden = await self.forbidden_hosts(project_id)
        grouped: dict[str, list[ConnectorHost]] = {}
        for host in hosts:
            domain = host.registrable
            if domain in owned or domain in IGNORED_DOMAINS:
                continue
            if domain.rsplit(".", 1)[-1] in PRIVATE_TLDS:
                continue
            grouped.setdefault(domain, []).append(host)

        out = [
            DiscoveredDomain(
                domain=domain,
                reason=RelatedReason.PROXY_TRAFFIC.value,
                reason_label=RELATED_REASON_LABELS[RelatedReason.PROXY_TRAFFIC.value],
                reason_detail=RELATED_REASON_DETAIL[RelatedReason.PROXY_TRAFFIC.value],
                hostnames=sorted(h.host for h in members)[:MAX_DISCOVERED_HOSTNAMES],
                hostname_count=len(members),
                requests=sum(h.requests for h in members),
                out_of_scope=(
                    self._forbidden(domain, forbidden)
                    or self._covers_forbidden(domain, forbidden)
                )
                is not None,
                program=self._forbidden(domain, forbidden)
                or self._covers_forbidden(domain, forbidden),
                first_seen_at=min(h.first_seen_at for h in members),
                last_seen_at=max(h.last_seen_at for h in members),
            )
            for domain, members in grouped.items()
        ]
        out.sort(
            key=lambda d: (not d.out_of_scope, -d.requests, -d.hostname_count, d.domain)
        )
        return out[:MAX_DISCOVERED]

    async def dismiss_domain(
        self, connector_id: uuid.UUID, project_id: uuid.UUID, domain: str
    ) -> int:
        await self.get(connector_id, project_id)
        result = await self.session.execute(
            update(ConnectorHost)
            .where(
                ConnectorHost.connector_id == connector_id,
                ConnectorHost.registrable == domain.strip().lower(),
            )
            .values(dismissed=True)
        )
        await self.session.commit()
        return result.rowcount or 0

    async def add_target(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        created_by: uuid.UUID,
        domain: str,
        scan: bool = False,
    ) -> TargetAdded:
        """Promote a discovered domain to a target, then re-attribute the hosts under it."""
        from app.services.target import TargetService  # noqa: PLC0415

        row = await self.get(connector_id, project_id)
        value = domain.strip().lower()
        if not registrable_domain(value):
            msg = f"{domain!r} is not a domain."
            raise ConnectorError(msg)
        program = self._forbidden(value, await self.forbidden_hosts(project_id))
        if program:
            msg = (
                f"{value} is out of scope for {program}. Testing it is not authorised."
            )
            raise ConnectorError(msg)
        targets = await TargetService(self.session).ensure_targets(
            [value], project_id, created_by
        )
        if not targets:
            msg = "The target could not be created."
            raise ConnectorError(msg)
        target_id = targets[0].id
        await self.session.execute(
            update(ConnectorHost)
            .where(
                ConnectorHost.connector_id == row.id,
                ConnectorHost.registrable == value,
            )
            .values(target_id=target_id)
        )
        attached = await self.session.execute(
            update(ConnectorCandidate)
            .where(
                ConnectorCandidate.connector_id == row.id,
                ConnectorCandidate.target_id.is_(None),
                or_(
                    ConnectorCandidate.host == value,
                    ConnectorCandidate.host.endswith(f".{value}"),
                ),
            )
            .values(target_id=target_id)
        )
        await self.session.commit()
        scan_id = (
            await self._first_scan(target_id, project_id, created_by) if scan else None
        )
        return TargetAdded(
            target_id=target_id,
            target_value=value,
            attached=attached.rowcount or 0,
            scan_id=scan_id,
        )

    async def _first_scan(
        self, target_id: uuid.UUID, project_id: uuid.UUID, created_by: uuid.UUID
    ) -> uuid.UUID:
        """A full run."""
        from app.services.scan import ScanService  # noqa: PLC0415

        run = await ScanService(self.session).create(
            ScanCreate(engine_id=None, target_id=target_id),
            project_id,
            created_by,
        )
        return run.id

    async def _programs(
        self, project_id: uuid.UUID
    ) -> list[tuple[uuid.UUID, str, int]]:
        """Programs whose scope resolved to a target in this project."""
        rows = (
            await self.session.execute(
                select(
                    BountyProgram.id,
                    BountyProgram.name,
                    func.count(func.distinct(Target.id)),
                )
                .join(BountyScope, BountyScope.program_id == BountyProgram.id)
                .join(Target, Target.target_value == BountyScope.target_value)
                .where(Target.project_id == project_id)
                .group_by(BountyProgram.id, BountyProgram.name)
                .order_by(BountyProgram.name)
            )
        ).all()
        return [(i, n, c) for i, n, c in rows]

    async def forbidden_hosts(self, project_id: uuid.UUID) -> dict[str, str]:
        """Host patterns a program forbids, and which program forbids them."""
        rows = (
            await self.session.execute(
                select(BountyScope.asset_identifier, BountyProgram.name)
                .join(BountyProgram, BountyProgram.id == BountyScope.program_id)
                .where(
                    BountyScope.scope_state == ScopeState.OUT_OF_SCOPE.value,
                    BountyScope.program_id.in_(
                        select(BountyScope.program_id)
                        .join(Target, Target.target_value == BountyScope.target_value)
                        .where(Target.project_id == project_id)
                    ),
                )
            )
        ).all()
        out: dict[str, str] = {}
        for identifier, program in rows:
            value = (identifier or "").strip().lower().removeprefix("*.").rstrip("/")
            for prefix in ("https://", "http://"):
                value = value.removeprefix(prefix)
            value = value.split("/", 1)[0]
            if value:
                out.setdefault(value, program)
        return out

    @staticmethod
    def _forbidden(host: str, patterns: dict[str, str]) -> str | None:
        """The program that forbids this exact host, or a parent of it."""
        for pattern, program in patterns.items():
            if _host_matches(host, pattern):
                return program
        return None

    @staticmethod
    def _covers_forbidden(domain: str, patterns: dict[str, str]) -> str | None:
        """The program that forbids something *under* this domain."""
        for pattern, program in patterns.items():
            if _host_matches(pattern, domain):
                return program
        return None

    async def _targets_all(self, project_id: uuid.UUID) -> list[tuple[uuid.UUID, str]]:
        rows = await self.session.execute(
            select(Target.id, Target.target_value).where(
                Target.project_id == project_id
            )
        )
        return [(i, v) for i, v in rows.all()]

    async def _touch_session(
        self,
        row: Connector,
        client: str | None,
        hosts: set[str],
        seen: int,
        novel: int,
        now,
    ) -> None:
        """Only hosts that passed the scope filter are stored."""
        if not row.capture_sessions:
            return
        cutoff = now - timedelta(minutes=SESSION_GAP_MINUTES)
        current = await self.session.scalar(
            select(ConnectorSession)
            .where(
                ConnectorSession.connector_id == row.id,
                ConnectorSession.last_event_at >= cutoff,
            )
            .order_by(ConnectorSession.last_event_at.desc())
            .limit(1)
        )
        if current is None:
            current = ConnectorSession(
                connector_id=row.id, client=(client or None), started_at=now
            )
            self.session.add(current)
        current.hosts = sorted({*(current.hosts or []), *hosts})[:50]
        current.requests += seen
        current.novel += novel
        current.last_event_at = now

    def _ready(self, row: Connector, queued: int, now) -> bool:
        """Whether the queue may be scanned without an explicit request."""
        if row.sync_trigger == SyncTrigger.MANUAL.value or not queued:
            return False
        if queued >= row.queue_threshold:
            return True
        if row.sync_trigger == SyncTrigger.QUIET.value and row.last_seen_at:
            quiet = (now - row.last_seen_at).total_seconds() / 60
            return quiet >= row.quiet_minutes
        return False

    # reading --------------------------------------------------------------

    async def candidates(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        state: str | None = None,
        host: str | None = None,
        notice: str | None = None,
        search: str | None = None,
        page: int = 1,
    ) -> CandidatePage:
        await self.get(connector_id, project_id)
        base = select(ConnectorCandidate).where(
            ConnectorCandidate.connector_id == connector_id
        )
        if state:
            base = base.where(ConnectorCandidate.state == state)
        if host:
            base = base.where(ConnectorCandidate.host == host)
        if notice:
            base = base.where(
                cast(ConnectorCandidate.notices, JSONB).contains([notice])
            )
        if search:
            base = base.where(ConnectorCandidate.url.ilike(f"%{search.strip()}%"))
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(*_RANK)
                    .offset((max(page, 1) - 1) * PAGE_SIZE)
                    .limit(PAGE_SIZE)
                )
            )
            .scalars()
            .all()
        )
        counts = dict(
            (
                await self.session.execute(
                    select(ConnectorCandidate.state, func.count())
                    .where(ConnectorCandidate.connector_id == connector_id)
                    .group_by(ConnectorCandidate.state)
                )
            ).all()
        )
        hosts = [
            {"host": h, "count": c, "unknown": u or 0}
            for h, c, u in (
                await self.session.execute(
                    select(
                        ConnectorCandidate.host,
                        func.count(),
                        func.count().filter(ConnectorCandidate.known.is_(False)),
                    )
                    .where(ConnectorCandidate.connector_id == connector_id)
                    .group_by(ConnectorCandidate.host)
                    .order_by(func.count().desc())
                    .limit(30)
                )
            ).all()
        ]
        return CandidatePage(
            rows=[self._candidate_read(r) for r in rows],
            total=total or 0,
            counts=dict(counts),
            hosts=hosts,
        )

    async def queue_actions(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        ids: list[uuid.UUID],
        kind: str,
    ) -> int:
        """Hand chosen shapes back to the proxy."""
        row = await self.get(connector_id, project_id)
        if kind not in {k.value for k in ActionKind}:
            msg = f"Unknown action {kind!r}."
            raise ConnectorError(msg)
        pending = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorAction)
            .where(
                ConnectorAction.connector_id == row.id,
                ConnectorAction.delivered_at.is_(None),
            )
        )
        if (pending or 0) + len(ids) > MAX_PENDING_ACTIONS:
            msg = f"{MAX_PENDING_ACTIONS} actions are already waiting to be collected."
            raise ConnectorError(msg)
        picked = (
            (
                await self.session.execute(
                    select(ConnectorCandidate).where(
                        ConnectorCandidate.connector_id == row.id,
                        ConnectorCandidate.id.in_(ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        if not picked:
            msg = "Nothing was selected."
            raise ConnectorError(msg)
        self.session.add_all(
            [
                ConnectorAction(
                    connector_id=row.id,
                    kind=kind,
                    url=candidate.url,
                    method=(candidate.methods or ["GET"])[0],
                    label=candidate.path[:120],
                )
                for candidate in picked
            ]
        )
        await self.session.commit()
        return len(picked)

    async def queue_endpoint_actions(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        endpoints: list[Endpoint],
        kind: str,
    ) -> int:
        """Hand discovered endpoints to the proxy, the same queue the candidates use."""
        row = await self.get(connector_id, project_id)
        if kind not in {k.value for k in ActionKind}:
            msg = f"Unknown action {kind!r}."
            raise ConnectorError(msg)
        rows = [e for e in endpoints if e.project_id == project_id]
        if not rows:
            msg = "Nothing was selected."
            raise ConnectorError(msg)
        pending = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorAction)
            .where(
                ConnectorAction.connector_id == row.id,
                ConnectorAction.delivered_at.is_(None),
            )
        )
        if (pending or 0) + len(rows) > MAX_PENDING_ACTIONS:
            msg = f"{MAX_PENDING_ACTIONS} actions are already waiting to be collected."
            raise ConnectorError(msg)
        self.session.add_all(
            [
                ConnectorAction(
                    connector_id=row.id,
                    kind=kind,
                    url=e.url,
                    method=(e.methods or ["GET"])[0],
                    label=e.path[:120],
                )
                for e in rows
            ]
        )
        await self.session.commit()
        return len(rows)

    async def take_notices(self, row: Connector) -> list[NoticeRead]:
        """What reNgine wants said while the tester is still testing."""
        pending = (
            (
                await self.session.execute(
                    select(ConnectorCandidate)
                    .where(
                        ConnectorCandidate.connector_id == row.id,
                        ConnectorCandidate.notified_at.is_(None),
                        cast(ConnectorCandidate.notices, JSONB).has_any(
                            array(tuple(LOUD_NOTICES))
                        ),
                    )
                    .order_by(ConnectorCandidate.last_seen_at.desc())
                    .limit(MAX_NOTICE_BATCH)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        now = utc_now()
        out: list[NoticeRead] = []
        for candidate in pending:
            candidate.notified_at = now
            loudest = next(
                (n for n in NOTICE_ORDER if n in (candidate.notices or [])), None
            )
            if loudest is None:
                continue
            out.append(
                NoticeRead(
                    kind=loudest,
                    label=NOTICE_LABELS.get(loudest, loudest),
                    url=candidate.url,
                    host=candidate.host,
                    status_code=candidate.status_code,
                    seen_at=candidate.last_seen_at,
                )
            )
        await self.session.commit()
        return out

    async def record_finding(
        self, row: Connector, report: FindingReport, created_by: uuid.UUID | None
    ) -> FindingRecorded:
        """A person confirmed something."""
        parsed = parse_url(report.url)
        if parsed is None:
            msg = "That URL could not be read."
            raise ConnectorError(msg)
        if report.severity not in {s.value for s in Severity}:
            msg = f"Unknown severity {report.severity!r}."
            raise ConnectorError(msg)
        targets = await self._targets_all(row.project_id)
        target_id = self._resolve_target(parsed.host, targets)
        if target_id is None:
            msg = f"{parsed.host} does not belong to a target in this project."
            raise ConnectorError(msg)
        target_value = next(v for i, v in targets if i == target_id)

        scan_id = await self._manual_run(row, target_id, created_by)
        title = strip_control(report.title).strip()[:500] or "Manual finding"
        template_id = f"manual:{row.kind}"
        mark = fingerprint(Scanner.MANUAL.value, template_id, title, parsed.url)
        existing = await self.session.scalar(
            select(Vulnerability.id).where(
                Vulnerability.scan_id == scan_id, Vulnerability.fingerprint == mark
            )
        )
        if existing is None:
            finding = Vulnerability(
                scan_id=scan_id,
                target_id=target_id,
                project_id=row.project_id,
                fingerprint=mark,
                scanner=Scanner.MANUAL.value,
                template_id=template_id,
                template_name=title,
                severity=report.severity,
                protocol=Protocol.HTTP.value,
                matched_at=parsed.url,
                host=parsed.host,
                port=parsed.port,
                scheme=parsed.scheme,
                description=strip_control(report.notes)[:8000]
                if report.notes
                else None,
                request=strip_control(report.request)[:200_000]
                if report.request
                else None,
                response=strip_control(report.response)[:200_000]
                if report.response
                else None,
            )
            self.session.add(finding)
            await self.session.commit()
            stored = finding.id
        else:
            stored = existing
        total = await self.session.scalar(
            select(func.count())
            .select_from(Vulnerability)
            .where(Vulnerability.scan_id == scan_id)
        )
        return FindingRecorded(
            finding_id=stored,
            scan_id=scan_id,
            target_value=target_value,
            total=total or 0,
        )

    async def _manual_run(
        self, row: Connector, target_id: uuid.UUID, created_by: uuid.UUID | None
    ) -> uuid.UUID:
        """One run per connector and target, holding what a person found by hand."""
        label = f"{MANUAL_RUN_LABEL} · {row.name}"[:200]
        existing = await self.session.scalar(
            select(Scan.id)
            .where(
                Scan.project_id == row.project_id,
                Scan.target_id == target_id,
                Scan.engine_name == label,
            )
            .order_by(Scan.created_at.desc())
            .limit(1)
        )
        if existing:
            return existing
        now = utc_now()
        run = Scan(
            project_id=row.project_id,
            target_id=target_id,
            engine_id=None,
            engine_name=label,
            scope=ScanScope.FOCUSED.value,
            status=ScanStatus.COMPLETED.value,
            execution_config={"manual": True, "connector": str(row.id)},
            started_at=now,
            completed_at=now,
            created_by=created_by,
        )
        self.session.add(run)
        await self.session.commit()
        return run.id

    async def take_actions(self, row: Connector) -> list[ActionRead]:
        """Collected by the proxy, delivered once."""
        cutoff = utc_now() - timedelta(minutes=ACTION_TTL_MINUTES)
        await self.session.execute(
            delete(ConnectorAction).where(
                ConnectorAction.connector_id == row.id,
                ConnectorAction.delivered_at.is_(None),
                ConnectorAction.created_at < cutoff,
            )
        )
        pending = (
            (
                await self.session.execute(
                    select(ConnectorAction)
                    .where(
                        ConnectorAction.connector_id == row.id,
                        ConnectorAction.delivered_at.is_(None),
                    )
                    .order_by(ConnectorAction.created_at)
                    .limit(MAX_ACTION_BATCH)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        now = utc_now()
        for action in pending:
            action.delivered_at = now
        await self.session.commit()
        return [
            ActionRead(kind=a.kind, url=a.url, method=a.method, label=a.label)
            for a in pending
        ]

    async def coverage(
        self, connector_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[ConnectorCoverage]:
        """Scanned endpoints per host against shapes captured through the proxy."""
        row = await self.get(connector_id, project_id)
        browsed = (
            await self.session.execute(
                select(
                    ConnectorCandidate.host,
                    func.count(),
                    func.count().filter(ConnectorCandidate.known.is_(False)),
                )
                .where(ConnectorCandidate.connector_id == connector_id)
                .group_by(ConnectorCandidate.host)
            )
        ).all()
        if not browsed:
            return []
        hosts = [h for h, _, _ in browsed]
        seen = {
            h: (sig or set())
            for h, sig in (
                (
                    await self.session.execute(
                        select(
                            ConnectorCandidate.host,
                            func.array_agg(ConnectorCandidate.signature),
                        )
                        .where(ConnectorCandidate.connector_id == connector_id)
                        .group_by(ConnectorCandidate.host)
                    )
                ).all()
            )
        }
        known_rows = (
            await self.session.execute(
                select(
                    Endpoint.host,
                    func.count(func.distinct(Endpoint.signature)),
                    func.array_agg(func.distinct(Endpoint.signature)),
                )
                .where(Endpoint.project_id == row.project_id, Endpoint.host.in_(hosts))
                .group_by(Endpoint.host)
            )
        ).all()
        known_map = {h: (total, set(sigs or [])) for h, total, sigs in known_rows}
        out: list[ConnectorCoverage] = []
        for host, _browsed, unknown in browsed:
            total, sigs = known_map.get(host, (0, set()))
            visited = len(sigs & set(seen.get(host) or []))
            out.append(
                ConnectorCoverage(
                    host=host,
                    known_endpoints=total,
                    visited=visited,
                    unvisited=max(total - visited, 0),
                    unvisited_interesting=0,
                    browsed_unknown=unknown or 0,
                )
            )
        out.sort(key=lambda c: (-c.unvisited, -c.known_endpoints))
        return out

    async def sessions(
        self, connector_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[SessionRead]:
        await self.get(connector_id, project_id)
        rows = (
            (
                await self.session.execute(
                    select(ConnectorSession)
                    .where(ConnectorSession.connector_id == connector_id)
                    .order_by(ConnectorSession.last_event_at.desc())
                    .limit(MAX_SESSIONS)
                )
            )
            .scalars()
            .all()
        )
        return [
            SessionRead(
                id=r.id,
                client=r.client,
                hosts=list(r.hosts or []),
                requests=r.requests,
                novel=r.novel,
                started_at=r.started_at,
                last_event_at=r.last_event_at,
            )
            for r in rows
        ]

    # acting ---------------------------------------------------------------

    async def set_state(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        ids: list[uuid.UUID],
        state: str,
    ) -> int:
        await self.get(connector_id, project_id)
        if state not in {s.value for s in CandidateState}:
            msg = f"Unknown state {state!r}."
            raise ConnectorError(msg)
        result = await self.session.execute(
            update(ConnectorCandidate)
            .where(
                ConnectorCandidate.connector_id == connector_id,
                ConnectorCandidate.id.in_(ids),
            )
            .values(state=state)
        )
        await self.session.commit()
        return result.rowcount or 0

    async def clear(self, connector_id: uuid.UUID, project_id: uuid.UUID) -> int:
        row = await self.get(connector_id, project_id)
        result = await self.session.execute(
            delete(ConnectorCandidate).where(
                ConnectorCandidate.connector_id == connector_id
            )
        )
        row.candidates = 0
        await self.session.commit()
        return result.rowcount or 0

    async def scan(
        self,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        created_by: uuid.UUID,
        ids: list[uuid.UUID] | None = None,
    ):
        """Dispatch the queue as one focused scan of exactly those URLs."""
        from app.services.rescan import focused_overrides  # noqa: PLC0415
        from app.services.scan import ScanService  # noqa: PLC0415

        row = await self.get(connector_id, project_id)
        query = select(ConnectorCandidate).where(
            ConnectorCandidate.connector_id == connector_id,
            ConnectorCandidate.state == CandidateState.NEW.value,
        )
        if ids:
            query = query.where(ConnectorCandidate.id.in_(ids))
        picked = (await self.session.execute(query.limit(MAX_QUEUE))).scalars().all()
        if row.scan_safe_methods_only:
            picked = [
                c
                for c in picked
                if not c.methods or any(m.upper() in SAFE_METHODS for m in c.methods)
            ]
        picked = [c for c in picked if c.target_id][:MAX_CANDIDATE_SCAN]
        if not picked:
            msg = "No queued shape belongs to a target in this project."
            raise ConnectorError(msg)
        target_id = picked[0].target_id
        assets = [c.url for c in picked if c.target_id == target_id]
        scan = await ScanService(self.session).create(
            ScanCreate(
                engine_id=None,
                context_id=row.context_id,
                target_id=target_id,
                overrides=focused_overrides(list(stages_for(_DIMENSION))),
                seed_assets=[
                    SeedAsset(kind=SeedKind.URL.value, value=value) for value in assets
                ],
                dimension=_DIMENSION,
            ),
            project_id,
            created_by,
        )
        await self.session.execute(
            update(ConnectorCandidate)
            .where(ConnectorCandidate.id.in_([c.id for c in picked]))
            .values(state=CandidateState.QUEUED.value, scan_id=scan.id)
        )
        row.scans_launched += 1
        row.last_scan_at = utc_now()
        await self.session.commit()
        return scan

    # helpers --------------------------------------------------------------

    async def _program_targets(
        self, program_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[tuple[uuid.UUID, str]]:
        rows = (
            await self.session.execute(
                select(Target.id, Target.target_value)
                .join(BountyScope, BountyScope.target_value == Target.target_value)
                .where(
                    Target.project_id == project_id,
                    BountyScope.program_id == program_id,
                    BountyScope.scope_state == ScopeState.IN_SCOPE.value,
                )
                .distinct()
            )
        ).all()
        return [(i, v) for i, v in rows]

    async def _chosen_target(
        self, target_id: uuid.UUID | None, project_id: uuid.UUID
    ) -> uuid.UUID | None:
        """The target the operator picked in the proxy, if it belongs to this project."""
        if target_id is None:
            return None
        target = await self.session.get(Target, target_id)
        return target.id if target and target.project_id == project_id else None

    async def target_options(self, row: Connector) -> list[TargetOption]:
        """The picker the proxy shows while testing."""
        rows = (
            await self.session.execute(
                select(
                    Target.id,
                    Target.target_value,
                    Target.target_type,
                    func.count(func.distinct(Endpoint.signature)),
                )
                .outerjoin(Endpoint, Endpoint.target_id == Target.id)
                .where(Target.project_id == row.project_id)
                .group_by(Target.id, Target.target_value, Target.target_type)
                .order_by(Target.target_value)
                .limit(MAX_PICKER_TARGETS)
            )
        ).all()
        options = [
            TargetOption(
                id=identifier,
                value=value,
                target_type=str(getattr(kind, "value", kind)),
                kind="target",
                scanned=endpoints > 0,
                endpoints=endpoints,
            )
            for identifier, value, kind, endpoints in rows
        ]
        options.extend(
            TargetOption(
                id=identifier,
                value=name,
                target_type="program",
                kind="program",
                targets=count,
            )
            for identifier, name, count in await self._programs(row.project_id)
        )
        return options

    async def program_scope(
        self, row: Connector, program_id: uuid.UUID
    ) -> ConnectorScope:
        """A program's own scope, available the moment it is imported."""
        rows = (
            await self.session.execute(
                select(
                    BountyScope.asset_identifier,
                    BountyScope.scope_state,
                    BountyProgram.name,
                )
                .join(BountyProgram, BountyProgram.id == BountyScope.program_id)
                .where(
                    BountyScope.program_id == program_id,
                    BountyScope.program_id.in_(
                        select(BountyScope.program_id)
                        .join(Target, Target.target_value == BountyScope.target_value)
                        .where(Target.project_id == row.project_id)
                    ),
                )
            )
        ).all()
        if not rows:
            msg = "No scope is recorded for that program in this project."
            raise ConnectorError(msg)
        include: set[str] = set()
        exclude: set[str] = set()
        name = rows[0][2]
        for identifier, state, _ in rows:
            value = (identifier or "").strip().removeprefix("*.")
            if not value:
                continue
            if state == ScopeState.OUT_OF_SCOPE.value:
                exclude.add(value)
            else:
                include.add(value)
        return ConnectorScope(
            target_value=name,
            include=sorted(_as_url(v) for v in include),
            exclude=sorted(_as_url(v) for v in exclude),
            hosts_known=len(include),
            truncated=False,
            from_program=name,
            from_scope_rules=True,
        )

    async def scope_for(self, row: Connector, target_id: uuid.UUID) -> ConnectorScope:
        """Scope rules for the proxy: the hostnames reNgine found, and a program's exclusions."""
        target = await self.session.get(Target, target_id)
        if target is None or target.project_id != row.project_id:
            msg = "That target does not belong to this project."
            raise ConnectorError(msg)

        hosts = [
            name
            for (name,) in (
                await self.session.execute(
                    select(Subdomain.name)
                    .where(Subdomain.target_id == target.id)
                    .distinct()
                    .order_by(Subdomain.name)
                    .limit(MAX_SCOPE_HOSTS + 1)
                )
            ).all()
        ]
        truncated = len(hosts) > MAX_SCOPE_HOSTS
        hosts = hosts[:MAX_SCOPE_HOSTS]
        include = {target.target_value, *hosts}

        program = None
        exclude: set[str] = set()
        rows = (
            await self.session.execute(
                select(
                    BountyScope.asset_identifier,
                    BountyScope.scope_state,
                    BountyProgram.name,
                )
                .join(BountyProgram, BountyProgram.id == BountyScope.program_id)
                .where(BountyScope.target_value == target.target_value)
            )
        ).all()
        for identifier, state, name in rows:
            value = (identifier or "").strip().removeprefix("*.")
            if not value:
                continue
            program = program or name
            if state == ScopeState.OUT_OF_SCOPE.value:
                exclude.add(value)
            else:
                include.add(value)

        return ConnectorScope(
            target_value=target.target_value,
            include=sorted(_as_url(h) for h in include if h),
            exclude=sorted(_as_url(h) for h in exclude if h),
            hosts_known=len(hosts),
            truncated=truncated,
            from_program=program,
        )

    async def host_facts(self, row: Connector, host: str) -> HostFacts:
        """What reNgine already knows about the host being tested."""
        name = (host or "").strip().lower()
        if not name:
            msg = "No host given."
            raise ConnectorError(msg)
        targets = await self._targets_all(row.project_id)
        target_id = self._resolve_target(name, targets)
        target_value = next((v for i, v in targets if i == target_id), None)

        scanned = {
            signature
            for (signature,) in (
                await self.session.execute(
                    select(Endpoint.signature)
                    .where(Endpoint.project_id == row.project_id, Endpoint.host == name)
                    .distinct()
                )
            ).all()
        }
        seen = {
            signature
            for (signature,) in (
                await self.session.execute(
                    select(ConnectorCandidate.signature).where(
                        ConnectorCandidate.connector_id == row.id,
                        ConnectorCandidate.host == name,
                    )
                )
            ).all()
        }
        flagged = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(
                ConnectorCandidate.connector_id == row.id,
                ConnectorCandidate.host == name,
                func.json_array_length(ConnectorCandidate.notices) > 0,
            )
        )
        last_scan = (
            await self.session.scalar(
                select(func.max(Scan.completed_at)).where(
                    Scan.project_id == row.project_id, Scan.target_id == target_id
                )
            )
            if target_id
            else None
        )

        return HostFacts(
            host=name,
            target_value=target_value,
            known_endpoints=len(scanned),
            visited=len(scanned & seen),
            unvisited=max(len(scanned) - len(scanned & seen), 0),
            flagged=flagged or 0,
            last_scan_at=last_scan,
        )

    def _resolve_target(
        self, host: str, targets: list[tuple[uuid.UUID, str]]
    ) -> uuid.UUID | None:
        best: tuple[int, uuid.UUID] | None = None
        for target_id, value in targets:
            if _host_matches(host, value or "") and (
                best is None or len(value) > best[0]
            ):
                best = (len(value), target_id)
        return best[1] if best else None

    async def _known_signatures(
        self, project_id: uuid.UUID, signatures: list[str]
    ) -> set[str]:
        if not signatures:
            return set()
        rows = await self.session.execute(
            select(Endpoint.signature).where(
                Endpoint.project_id == project_id,
                Endpoint.signature.in_(signatures),
            )
        )
        return {s for (s,) in rows.all()}

    async def _count(
        self, connector_id: uuid.UUID, states: tuple[str, ...] | None = None
    ) -> int:
        query = (
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(ConnectorCandidate.connector_id == connector_id)
        )
        if states:
            query = query.where(ConnectorCandidate.state.in_(states))
        return await self.session.scalar(query) or 0

    def _setup(self, row: Connector, secret: str, base_url: str = "") -> dict:
        """The proxy runs on someone's laptop."""
        spec = connector_for(row.kind)
        if spec is None:
            return {}
        endpoint = f"{base_url.rstrip('/')}/api/v1/connectors/ingest"
        return {
            "endpoint": endpoint,
            "steps": [
                {
                    "title": step.title,
                    "detail": step.detail,
                    "code": step.code,
                    "lang": step.lang,
                }
                for step in spec.setup(endpoint=endpoint, secret=secret)
            ],
        }

    def _candidate_read(self, row: ConnectorCandidate) -> CandidateRead:
        return CandidateRead(
            id=row.id,
            target_id=row.target_id,
            url=row.url,
            host=row.host,
            path=row.path,
            methods=list(row.methods or []),
            params=list(row.params or []),
            param_count=row.param_count,
            endpoint_class=row.endpoint_class,
            interests=list(row.interests or []),
            notices=list(row.notices or []),
            status_code=row.status_code,
            content_type=row.content_type,
            title=row.title,
            authenticated=row.authenticated,
            source_tool=row.source_tool,
            known=row.known,
            state=row.state,
            hits=row.hits,
            scan_id=row.scan_id,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
        )

    async def _read(
        self, row: Connector, owned: set[str] | None = None
    ) -> ConnectorRead:
        now = utc_now()
        minutes = (
            (now - row.last_seen_at).total_seconds() / 60 if row.last_seen_at else None
        )
        queued = await self._count(row.id, states=(CandidateState.NEW.value,))
        unseen = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(
                ConnectorCandidate.connector_id == row.id,
                ConnectorCandidate.known.is_(False),
            )
        )
        unassigned = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(
                ConnectorCandidate.connector_id == row.id,
                ConnectorCandidate.target_id.is_(None),
            )
        )
        flagged = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorCandidate)
            .where(
                ConnectorCandidate.connector_id == row.id,
                func.json_array_length(ConnectorCandidate.notices) > 0,
            )
        )
        discovered = len(await self.discovered(row.id, row.project_id, owned=owned))
        pending_actions = await self.session.scalar(
            select(func.count())
            .select_from(ConnectorAction)
            .where(
                ConnectorAction.connector_id == row.id,
                ConnectorAction.delivered_at.is_(None),
            )
        )
        return ConnectorRead(
            id=row.id,
            project_id=row.project_id,
            kind=row.kind,
            name=row.name,
            token_prefix=row.token_prefix,
            only_known_hosts=row.only_known_hosts,
            sync_trigger=row.sync_trigger,
            quiet_minutes=row.quiet_minutes,
            queue_threshold=row.queue_threshold,
            ingest_tools=list(row.ingest_tools or []),
            capture_bodies=row.capture_bodies,
            capture_sessions=row.capture_sessions,
            record_hosts=row.record_hosts,
            include_static=row.include_static,
            scan_safe_methods_only=row.scan_safe_methods_only,
            context_id=row.context_id,
            paused=row.paused,
            state=state_for(minutes, row.paused),
            requests_seen=row.requests_seen,
            dropped_out_of_scope=row.dropped_out_of_scope,
            candidates=row.candidates,
            queued=queued,
            unseen=unseen or 0,
            unassigned=unassigned or 0,
            flagged=flagged or 0,
            discovered=discovered,
            scans_launched=row.scans_launched,
            pending_actions=pending_actions or 0,
            last_seen_at=row.last_seen_at,
            last_client=row.last_client,
            last_scan_at=row.last_scan_at,
            created_at=row.created_at,
        )


DEFAULT_KIND = ConnectorKind.BURP.value
