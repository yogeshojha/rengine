from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
import zlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import BaseAppSettings
from shared.definitions.ask import AskSubject
from shared.definitions.issue_trackers import TrackerKind
from shared.definitions.lookalikes import Verdict
from shared.definitions.scan_surface import SurfaceState
from shared.definitions.secrets import SecretGroup
from shared.definitions.vulnerabilities import Scanner, TemplateOrigin
from shared.definitions.watch import WatchHostState
from shared.enums.activity import ActivityEvent
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.scan import ScanActivityStatus
from shared.enums.target import TargetType
from shared.models import (
    ActivityLog,
    AskThread,
    CloudBucket,
    Connector,
    DomainPosture,
    Export,
    InterestDismissal,
    InterestRule,
    IpAddress,
    IssueTracker,
    LookalikeDomain,
    Note,
    Notification,
    Organization,
    Report,
    ScanCommand,
    ScanContext,
    ScanEngine,
    ScanSchedule,
    ScanTag,
    ScanTagLink,
    Secret,
    Tag,
    TrackedIssue,
    Tripwire,
    TripwireRun,
)
from shared.models.bounty_program import BountyProgram
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.project import Project
from shared.models.project_member import ProjectMember
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.subdomain import Subdomain
from shared.models.tag import TargetTag
from shared.models.target import Target, TargetOrganization
from shared.models.target_seed import TargetSeed
from shared.models.user import User
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage
from shared.models.watch import ProgramWatch, WatchHost
from shared.utils.datetime import utc_now

TEST_DB = os.environ.get("POSTGRES_TEST_DB", "rengine_test")
# one suite run per database at a time
_RUN_LOCK = zlib.crc32(TEST_DB.encode()) - 2**31
REPO_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC = shutil.which("alembic") or str(Path(sys.executable).parent / "alembic")


def _admin_url() -> str:
    s = BaseAppSettings()
    return (
        f"postgresql+asyncpg://{s.POSTGRES_USER}:{s.POSTGRES_PASSWORD}"
        f"@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/postgres"
    )


def _test_url(driver: str = "postgresql+asyncpg") -> str:
    s = BaseAppSettings()
    return (
        f"{driver}://{s.POSTGRES_USER}:{s.POSTGRES_PASSWORD}"
        f"@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/{TEST_DB}"
    )


@asynccontextmanager
async def _own_the_database() -> AsyncIterator[None]:
    """Recreate the test database and hold the lock for the whole run."""
    if TEST_DB == BaseAppSettings().POSTGRES_DB or not TEST_DB.endswith("_test"):
        pytest.exit(f"POSTGRES_TEST_DB must end in _test: {TEST_DB}", returncode=2)
    engine = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT pg_advisory_lock(:k)"), {"k": _RUN_LOCK})
            await conn.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": TEST_DB},
            )
            await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{TEST_DB}"'))
            await conn.execute(sa.text(f'CREATE DATABASE "{TEST_DB}"'))
            yield
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def database() -> AsyncIterator[str]:
    """A migrated database of its own."""
    async with _own_the_database():
        env = {**os.environ, "POSTGRES_DB": TEST_DB}
        proc = await asyncio.to_thread(
            subprocess.run,
            [ALEMBIC, "upgrade", "head"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            pytest.fail(f"alembic upgrade failed:\n{proc.stdout}\n{proc.stderr}")
        yield _test_url()


@pytest_asyncio.fixture(scope="session")
async def engine(database: str):
    eng = create_async_engine(database, future=True, poolclass=sa.pool.NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    """One transaction per test, rolled back."""
    async with engine.connect() as conn:
        outer = await conn.begin()
        s = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield s
        finally:
            await s.close()
            if outer.is_active:
                await outer.rollback()


class Estate:
    """A project, a target and the scans under it, addressed by name."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ):
        self.session = session
        self.project_id = project_id or uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.targets: dict[str, uuid.UUID] = {}
        self.scans: dict[str, uuid.UUID] = {}

    async def setup(self, *, name: str = "Test", with_user: bool = True) -> Estate:
        if with_user:
            self.session.add(
                User(
                    id=self.user_id,
                    username=f"t{self.user_id.hex[:8]}",
                    email=f"{self.user_id.hex[:8]}@test.local",
                    hashed_password="x",
                    is_superuser=True,
                )
            )
            await self.session.flush()
        self.slug = f"{name.lower().replace(' ', '-')}-{self.project_id.hex[:8]}"
        self.session.add(
            Project(
                id=self.project_id,
                name=name,
                slug=self.slug,
                created_by=self.user_id,
            )
        )
        await self.session.flush()
        return self

    async def sibling(
        self, name: str = "Other", project_id: uuid.UUID | None = None
    ) -> Estate:
        """A second project of the same administrator."""
        other = Estate(self.session, project_id=project_id, user_id=self.user_id)
        return await other.setup(name=name, with_user=False)

    async def member(
        self,
        *projects: uuid.UUID,
        user_id: uuid.UUID | None = None,
        can_create_projects: bool = False,
    ) -> User:
        """A standard user who opens these projects, this one when none is named."""
        user = User(
            id=user_id or uuid.uuid4(),
            username=f"m{uuid.uuid4().hex[:8]}",
            email=f"m{uuid.uuid4().hex[:8]}@test.local",
            hashed_password="x",
            can_create_projects=can_create_projects,
        )
        self.session.add(user)
        await self.session.flush()
        for project_id in projects or (self.project_id,):
            self.session.add(ProjectMember(project_id=project_id, user_id=user.id))
        await self.session.flush()
        return user

    async def canary(
        self, word: str, at: datetime, *, owner: uuid.UUID | None = None
    ) -> dict[str, Any]:
        """Rows of every kind a route reads, each text carrying the word, ids keyed by parameter name."""
        return await seed_canary(self, word, at, owner or self.user_id)

    async def target(
        self, value: str, kind: TargetType = TargetType.DOMAIN
    ) -> uuid.UUID:
        if value in self.targets:
            return self.targets[value]
        tid = uuid.uuid4()
        self.session.add(
            Target(
                id=tid,
                project_id=self.project_id,
                target_value=value,
                target_type=kind,
                created_by=self.user_id,
            )
        )
        await self.session.flush()
        self.targets[value] = tid
        return tid

    async def scan(
        self,
        target: str,
        name: str,
        *,
        at: datetime,
        status: str = "completed",
        config: dict | None = None,
        scope: str = "full",
        engine: str | None = None,
    ) -> uuid.UUID:
        tid = await self.target(target)
        sid = uuid.uuid4()
        self.session.add(
            Scan(
                id=sid,
                project_id=self.project_id,
                target_id=tid,
                engine_name=engine or name,
                execution_config=config or {},
                scope=scope,
                status=status,
                created_by=self.user_id,
                created_at=at,
                started_at=at,
                completed_at=at + timedelta(minutes=1),
            )
        )
        await self.session.flush()
        self.scans[name] = sid
        return sid

    async def hosts(
        self,
        scan: str,
        names: list[str],
        *,
        at: datetime,
        ips: list[str] | None = None,
        status: int | None = None,
        title: str | None = None,
        tech: list[str] | None = None,
        cname: str | None = None,
        webserver: str | None = None,
        cdn_name: str | None = None,
        favicon: str | None = None,
        sources: list[str] | None = None,
        phash: int | None = None,
    ) -> None:
        sid = self.scans[scan]
        target_id = await self._target_of(sid)
        for n in names:
            self.session.add(
                Subdomain(
                    project_id=self.project_id,
                    scan_id=sid,
                    target_id=target_id,
                    name=n,
                    discovered_at=at,
                    sources=sources or ["test"],
                    resolved_ips=ips or [],
                    http_status=status,
                    page_title=title,
                    tech=tech or [],
                    cname=cname,
                    webserver=webserver,
                    is_cdn=cdn_name is not None,
                    cdn_name=cdn_name,
                    favicon_hash=favicon,
                    screenshot_path=f"{sid}/screenshot/{n}.png" if phash else None,
                    screenshot_phash=phash,
                )
            )
        await self.session.flush()

    async def assets(
        self,
        scan: str,
        rows: list[str],
        *,
        at: datetime,
        ip: str | None = None,
        port: int = 443,
        status: int = 200,
        content_hash: str | None = None,
        jarm: str | None = None,
        issuer: str | None = None,
        body: str | None = None,
    ) -> None:
        sid = self.scans[scan]
        target_id = await self._target_of(sid)
        for host in rows:
            self.session.add(
                HttpAsset(
                    project_id=self.project_id,
                    scan_id=sid,
                    target_id=target_id,
                    url=f"https://{host}:{port}",
                    host=host,
                    port=port,
                    status_code=status,
                    ip=ip,
                    content_hash=content_hash,
                    response_body=body,
                    jarm=jarm,
                    tls_issuer=issuer,
                    discovered_at=at,
                )
            )
        await self.session.flush()

    async def endpoints(
        self,
        scan: str,
        paths: list[str],
        *,
        at: datetime,
        host: str = "www.example.com",
        status: int | None = None,
        kind: str = "page",
        sources: list[str] | None = None,
        interest: list[str] | None = None,
        params: int = 0,
    ) -> None:
        sid = self.scans[scan]
        target_id = await self._target_of(sid)
        for path in paths:
            directory, _, filename = path.rpartition("/")
            extension = filename.rpartition(".")[2] if "." in filename else None
            self.session.add(
                Endpoint(
                    project_id=self.project_id,
                    scan_id=sid,
                    target_id=target_id,
                    signature=uuid.uuid4().hex,
                    url=f"https://{host}{path}",
                    host=host,
                    path=path,
                    dir_path=f"{directory}/" if directory else "/",
                    filename=filename or None,
                    extension=extension,
                    endpoint_class=kind,
                    sources=sources or ["seed"],
                    primary_source=(sources or ["seed"])[0],
                    interest=interest or [],
                    param_count=params,
                    is_probed=status is not None,
                    status_code=status,
                    discovered_at=at,
                )
            )
        await self.session.flush()

    async def activity(
        self, scan: str, rows: dict[str, str], *, at: datetime | None = None
    ) -> None:
        sid = self.scans[scan]
        for name, state in rows.items():
            self.session.add(
                ScanActivity(
                    scan_id=sid,
                    project_id=self.project_id,
                    name=name,
                    title=name.replace("_", " ").title(),
                    status=state,
                    started_at=at,
                    completed_at=at,
                )
            )
        await self.session.flush()

    async def vulns(
        self,
        scan: str,
        rows: list[tuple[str, str]],
        *,
        at: datetime,
        host: str = "www.example.com",
        kev: bool = False,
        scanner: str = Scanner.NUCLEI.value,
        port: int | None = None,
        template: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        sid = self.scans[scan]
        target_id = await self._target_of(sid)
        for fingerprint, severity in rows:
            self.session.add(
                Vulnerability(
                    project_id=self.project_id,
                    scan_id=sid,
                    target_id=target_id,
                    fingerprint=fingerprint,
                    template_id=template or fingerprint,
                    template_name=(template or fingerprint).replace("-", " ").title(),
                    severity=severity,
                    matched_at=f"https://{host}/",
                    host=host,
                    port=port,
                    tags=tags or [],
                    is_kev=kev,
                    scanner=scanner,
                    discovered_at=at,
                )
            )
        await self.session.flush()

    async def surface(self, scan: str, hosts: list[str], *, port: int = 443) -> None:
        sid = self.scans[scan]
        target_id = await self._target_of(sid)
        for host in hosts:
            self.session.add(
                ScanSurfaceItem(
                    project_id=self.project_id,
                    scan_id=sid,
                    target_id=target_id,
                    value=f"https://{host}:{port}",
                    host=host,
                    port=port,
                    scheme="https",
                    state=SurfaceState.SCANNED.value,
                )
            )
        await self.session.flush()

    async def templates(
        self, rows: list[tuple[str, str]], *, at: datetime | None = None
    ) -> None:
        for template_id, severity in rows:
            self.session.add(
                VulnTemplate(
                    origin=TemplateOrigin.OFFICIAL.value,
                    template_id=template_id,
                    path=f"http/exposures/{template_id}.yaml",
                    name=template_id.replace("-", " ").title(),
                    severity=severity,
                    protocol="http",
                    created_at=at or utc_now(),
                )
            )
        await self.session.flush()

    async def triage(self, target: str, fingerprint: str, state: str) -> None:
        self.session.add(
            VulnerabilityTriage(
                project_id=self.project_id,
                target_id=await self.target(target),
                fingerprint=fingerprint,
                template_id=fingerprint,
                matched_at="",
                state=state,
            )
        )
        await self.session.flush()

    async def _target_of(self, scan_id: uuid.UUID) -> uuid.UUID:
        return await self.session.scalar(
            sa.select(Scan.target_id).where(Scan.id == scan_id)
        )

    async def ports(
        self,
        scan: str,
        rows: list[tuple[str, int, str]],
        *,
        at: datetime,
        product: str | None = None,
        version: str | None = None,
    ) -> None:
        sid = self.scans[scan]
        target_id = await self._target_of(sid)
        for ip, number, service in rows:
            self.session.add(
                Port(
                    project_id=self.project_id,
                    scan_id=sid,
                    target_id=target_id,
                    ip=ip,
                    number=number,
                    protocol="tcp",
                    service_name=service,
                    source="naabu",
                    product=product,
                    version=version,
                    discovered_at=at,
                )
            )
        await self.session.flush()


async def seed_canary(
    estate: Estate, word: str, at: datetime, owner: uuid.UUID
) -> dict[str, Any]:
    s = estate.session
    pid = estate.project_id
    apex = f"{word}.test"
    www, api = f"www.{apex}", f"api.{apex}"
    ip = "198.51.100.77"
    target_id = await estate.target(apex)
    scan_id = await estate.scan(apex, f"{word} census", at=at, engine=f"{word} engine")
    await estate.activity(
        f"{word} census",
        dict.fromkeys(
            (
                "subdomain_discovery",
                "http_probe",
                "port_scan",
                "url_discovery",
                "endpoint_probe",
                "vulnerability_scan",
            ),
            ScanActivityStatus.SUCCESS.value,
        ),
        at=at,
    )
    name = f"{word} census"
    await estate.hosts(
        name, [www, api], at=at, ips=[ip], status=200, title=f"{word} title"
    )
    await estate.assets(name, [www, api], at=at, ip=ip, body=f"{word} body")
    await estate.endpoints(name, [f"/{word}/login"], at=at, host=www, status=200)
    await estate.ports(name, [(ip, 443, "https")], at=at, product=word)
    fingerprint = f"{word}-fp"
    await estate.vulns(
        name, [(fingerprint, "high")], at=at, host=www, template=f"{word}-check"
    )
    await estate.surface(name, [www])
    s.add(
        IpAddress(
            scan_id=scan_id, target_id=target_id, project_id=pid, ip=ip, source=word
        )
    )

    def one(model, **fields):
        row = model(**fields)
        s.add(row)
        return row

    tag = one(
        Tag, name=f"{word} tag", slug=f"{word}-tag", project_id=pid, created_by=owner
    )
    org = one(
        Organization,
        name=f"{word} org",
        slug=f"{word}-org",
        project_id=pid,
        created_by=owner,
    )
    engine = one(ScanEngine, project_id=pid, created_by=owner, name=f"{word} engine")
    context = one(ScanContext, project_id=pid, created_by=owner, name=f"{word} context")
    program = one(
        BountyProgram,
        platform="hackerone",
        handle=f"h{uuid.uuid4().hex[:10]}",
        name="Program",
        program_state="open",
        submission_state="open",
    )
    tracker = one(
        IssueTracker,
        name="Tracker",
        kind=TrackerKind.GITHUB.value,
        url="https://github.com",
    )
    await s.flush()
    s.add(TargetTag(target_id=target_id, tag_id=tag.id))
    s.add(TargetOrganization(target_id=target_id, organization_id=org.id))
    scan_tag = one(ScanTag, project_id=pid, name=f"{word}-run")
    await s.flush()
    s.add(ScanTagLink(scan_id=scan_id, tag_id=scan_tag.id))
    schedule = one(
        ScanSchedule,
        project_id=pid,
        name=f"{word} nightly",
        target_ids=[str(target_id)],
        engine_id=engine.id,
        engine_name=engine.name,
        schedule_type="interval",
        interval_every=1,
        interval_unit="days",
        created_by=owner,
    )
    note = one(
        Note, project_id=pid, target_id=target_id, body=f"{word} note", created_by=owner
    )
    notification = one(
        Notification,
        type=NotificationType.SCAN,
        severity=NotificationSeverity.INFO,
        title=f"{word} alert",
        message=f"{word} message",
        project_id=pid,
    )
    one(
        ActivityLog,
        event_type=ActivityEvent.SCAN_COMPLETED,
        title=f"{word} scan completed",
        project_id=pid,
        target_id=target_id,
        scan_id=scan_id,
        target_value=apex,
    )
    tripwire = one(
        Tripwire,
        project_id=pid,
        name=f"{word} wire",
        dimension="web_assets",
        query=word,
    )
    export = one(
        Export,
        project_id=pid,
        dimension="web_assets",
        scan_id=scan_id,
        subject=f"{word} export",
        created_by=owner,
    )
    report = one(
        Report,
        project_id=pid,
        scan_id=scan_id,
        target_id=target_id,
        subject=f"{word} report",
        title=f"{word} report",
        created_by=owner,
    )
    rule = one(InterestRule, project_id=pid, name=f"{word} rule", kind=word, query=word)
    dismissal = one(
        InterestDismissal, target_id=target_id, project_id=pid, host=www, note=word
    )
    connector = one(
        Connector,
        project_id=pid,
        name=f"{word} burp",
        token_hash=uuid.uuid4().hex,
        token_prefix=word[:8],
    )
    secret = one(
        Secret,
        scan_id=scan_id,
        target_id=target_id,
        project_id=pid,
        fingerprint=uuid.uuid4().hex,
        kind="generic",
        group=SecretGroup.AUTH.value,
        value=f"{word}-secret-value",
        host=www,
        url=f"https://{www}/{word}.js",
    )
    command = one(
        ScanCommand,
        scan_id=scan_id,
        project_id=pid,
        tool="nuclei",
        command=f"nuclei -u {www}",
    )
    seed = one(TargetSeed, target_id=target_id, project_id=pid, value=f"seed.{apex}")
    one(
        CloudBucket,
        scan_id=scan_id,
        target_id=target_id,
        project_id=pid,
        name=f"{word}-bucket",
        provider="aws",
        url=f"https://{word}-bucket.s3.amazonaws.com",
        source="test",
        access="public",
    )
    one(
        DomainPosture,
        scan_id=scan_id,
        target_id=target_id,
        project_id=pid,
        zone=apex,
    )
    one(
        LookalikeDomain,
        scan_id=scan_id,
        target_id=target_id,
        project_id=pid,
        apex=apex,
        domain=f"{word}-login.test",
        display=f"{word}-login.test",
        technique="addition",
        verdict=Verdict.LIVE.value,
    )
    await s.flush()
    run = one(
        TripwireRun,
        tripwire_id=tripwire.id,
        project_id=pid,
        target_id=target_id,
        scan_id=scan_id,
        status="fired",
        rows=[{"key": www}],
        detail=word,
    )
    watch = one(ProgramWatch, project_id=pid, program_id=program.id, created_by=owner)
    issue = one(
        TrackedIssue,
        tracker_id=tracker.id,
        project_id=pid,
        target_id=target_id,
        template_id=f"{word}-check",
        severity="high",
        destination="owner/repo",
        title=f"{word} issue",
    )
    await s.flush()
    host = one(
        WatchHost,
        watch_id=watch.id,
        project_id=pid,
        target_id=target_id,
        name=f"new.{apex}",
        state=WatchHostState.NEW.value,
    )
    await s.flush()
    vulnerability_id = await s.scalar(
        sa.select(Vulnerability.id).where(Vulnerability.scan_id == scan_id)
    )
    return {
        "project_id": pid,
        "project_slug": estate.slug,
        "target_id": target_id,
        "scan_id": scan_id,
        "vulnerability_id": vulnerability_id,
        "fingerprint": fingerprint,
        "endpoint_id": await s.scalar(
            sa.select(Endpoint.id).where(Endpoint.scan_id == scan_id)
        ),
        "asset_id": await s.scalar(
            sa.select(HttpAsset.id).where(HttpAsset.scan_id == scan_id)
        ),
        "subdomain_id": await s.scalar(
            sa.select(Subdomain.id).where(Subdomain.scan_id == scan_id)
        ),
        "tag_id": tag.id,
        "organization_id": org.id,
        "engine_id": engine.id,
        "context_id": context.id,
        "schedule_id": schedule.id,
        "note_id": note.id,
        "notification_id": notification.uid,
        "tripwire_id": tripwire.id,
        "tripwire_run_id": run.id,
        "export_id": export.id,
        "report_id": report.id,
        "rule_id": rule.id,
        "dismissal_id": dismissal.id,
        "connector_id": connector.id,
        "secret_id": secret.id,
        "command_id": command.id,
        "seed_id": seed.id,
        "scan_tag_id": scan_tag.id,
        "watch_id": watch.id,
        "host_id": host.id,
        "issue_id": issue.id,
        "host": www,
        "ip": ip,
    }


async def ask_threads(
    estate: Estate, word: str, user_id: uuid.UUID, target_id: uuid.UUID
) -> dict[str, uuid.UUID]:
    """One asset thread and one estate thread of this user in the estate's project."""
    asset = AskThread(
        project_id=estate.project_id,
        target_id=target_id,
        user_id=user_id,
        asset_key=f"{word}-fp",
        title=f"{word} thread",
        message_count=1,
    )
    whole = AskThread(
        project_id=estate.project_id,
        subject=AskSubject.ESTATE.value,
        user_id=user_id,
        title=f"{word} estate thread",
        message_count=1,
    )
    estate.session.add_all([asset, whole])
    await estate.session.flush()
    return {"thread_id": asset.id, "estate_thread_id": whole.id}


@pytest.fixture
def flush_only(session: AsyncSession, monkeypatch) -> AsyncSession:
    """The test session with commit reduced to flush."""
    monkeypatch.setattr(session, "commit", session.flush)
    monkeypatch.setattr(session.sync_session, "commit", session.sync_session.flush)
    return session


@pytest_asyncio.fixture
async def estate(session: AsyncSession) -> Estate:
    return await Estate(session).setup()


async def _truncate(engine) -> None:
    """Truncate the roots; CASCADE clears the rest."""
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "TRUNCATE users, projects, instance_settings, issue_trackers, "
                "bounty_programs, notifications RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def durable(engine) -> AsyncIterator[AsyncSession]:
    """A session that may commit; tables are truncated around it."""
    await _truncate(engine)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        try:
            yield s
        finally:
            await s.rollback()
    await _truncate(engine)


@pytest_asyncio.fixture
async def durable_estate(durable: AsyncSession) -> Estate:
    return await Estate(durable).setup()


@pytest.fixture
def now() -> datetime:
    return utc_now()


class PriceCache:
    """The shared copy of the price catalog, private to one test."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttl: dict[str, int | None] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        self.ttl[key] = ex
        return True

    def delete(self, key: str) -> None:
        self.data.pop(key, None)


@pytest.fixture(autouse=True)
def _state_reachable(monkeypatch) -> None:
    import shared.redis  # noqa: PLC0415

    monkeypatch.setattr(shared.redis, "_state_down_until", 0.0)


@pytest.fixture(autouse=True)
def price_cache(monkeypatch) -> PriceCache:
    """No test reads the live price catalog over the network or from the shared cache."""
    from shared.services.ai import prices  # noqa: PLC0415

    def offline() -> dict:
        msg = "no network in tests"
        raise OSError(msg)

    cache = PriceCache()
    monkeypatch.setattr(prices, "sync_client", lambda: cache)
    monkeypatch.setattr(prices, "download", offline)
    prices.forget()
    yield cache
    prices.forget()
