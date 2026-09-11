from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import BaseAppSettings
from shared.enums.target import TargetType
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.project import Project
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.user import User
from shared.utils.datetime import utc_now

TEST_DB = os.environ.get("POSTGRES_TEST_DB", "rengine_test")
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


async def _recreate_database() -> None:
    engine = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(
            sa.text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": TEST_DB},
        )
        await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{TEST_DB}"'))
        await conn.execute(sa.text(f'CREATE DATABASE "{TEST_DB}"'))
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def database() -> AsyncIterator[str]:
    """A migrated database of its own."""
    await _recreate_database()
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
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        try:
            yield s
        finally:
            await s.rollback()


class Estate:
    """A project, a target and the scans under it, addressed by name."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.targets: dict[str, uuid.UUID] = {}
        self.scans: dict[str, uuid.UUID] = {}

    async def setup(self) -> Estate:
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
        self.session.add(
            Project(
                id=self.project_id,
                name="Test",
                slug=f"test-{self.project_id.hex[:8]}",
                created_by=self.user_id,
            )
        )
        await self.session.flush()
        return self

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
        self, target: str, name: str, *, at: datetime, status: str = "completed"
    ) -> uuid.UUID:
        tid = await self.target(target)
        sid = uuid.uuid4()
        self.session.add(
            Scan(
                id=sid,
                project_id=self.project_id,
                target_id=tid,
                engine_name=name,
                execution_config={},
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

    async def _target_of(self, scan_id: uuid.UUID) -> uuid.UUID:
        return await self.session.scalar(
            sa.select(Scan.target_id).where(Scan.id == scan_id)
        )

    async def ports(
        self, scan: str, rows: list[tuple[str, int, str]], *, at: datetime
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
                    discovered_at=at,
                )
            )
        await self.session.flush()


@pytest_asyncio.fixture
async def estate(session: AsyncSession) -> Estate:
    return await Estate(session).setup()


async def _truncate(engine) -> None:
    """Truncate the roots; CASCADE clears the rest."""
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "TRUNCATE users, projects, instance_settings RESTART IDENTITY CASCADE"
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
