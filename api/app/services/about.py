"""Version details of the instance and the tools it ships."""

from __future__ import annotations

import asyncio
import platform
import re
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import APP_VERSION
from shared.definitions.about import DOCUMENTATION_URL, ISSUE_URL, release_url
from shared.definitions.datasets import DatasetKind
from shared.definitions.toolchain import TOOLCHAIN
from shared.enums.instance import InstanceMode
from shared.logging import get_logger
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.threat_intel import ThreatFeed
from shared.redis import async_client

logger = get_logger(__name__)

REDIS_TIMEOUT_SECONDS = 3.0
_SERVER_VERSION = re.compile(r"^\d+(?:\.\d+)*")


class CheckLibraryRead(BaseModel):
    version: str | None = None
    checks: int | None = None
    synced_at: datetime | None = None


class ToolVersionRead(BaseModel):
    name: str
    version: str
    url: str


class AboutRead(BaseModel):
    version: str
    release_url: str | None = None
    mode: str
    architecture: str | None = None
    postgres: str | None = None
    redis: str | None = None
    check_library: CheckLibraryRead | None = None
    tools: list[ToolVersionRead]
    documentation_url: str
    issue_url: str


async def _mode(session: AsyncSession) -> str:
    found = await session.scalar(
        select(InstanceSettings.mode).where(
            InstanceSettings.singleton_key == SINGLETON_KEY
        )
    )
    return found or InstanceMode.BUG_BOUNTY.value


async def _postgres(session: AsyncSession) -> str | None:
    try:
        raw = await session.scalar(text("SHOW server_version"))
    except SQLAlchemyError:
        logger.debug("postgres version unreadable", exc_info=True)
        return None
    found = _SERVER_VERSION.match(str(raw or ""))
    return found.group(0) if found else None


async def _redis() -> str | None:
    try:
        info = await asyncio.wait_for(
            async_client().info("server"), timeout=REDIS_TIMEOUT_SECONDS
        )
    except Exception:
        logger.debug("redis version unreadable", exc_info=True)
        return None
    return info.get("redis_version") or None


async def _check_library(session: AsyncSession) -> CheckLibraryRead | None:
    row = await session.get(ThreatFeed, DatasetKind.LIBRARY.value)
    if row is None or row.last_synced_at is None:
        return None
    return CheckLibraryRead(
        version=row.version, checks=row.rows or None, synced_at=row.last_synced_at
    )


async def about(session: AsyncSession) -> AboutRead:
    return AboutRead(
        version=APP_VERSION,
        release_url=release_url(APP_VERSION),
        mode=await _mode(session),
        architecture=platform.machine() or None,
        postgres=await _postgres(session),
        redis=await _redis(),
        check_library=await _check_library(session),
        tools=[
            ToolVersionRead(name=tool.name, version=tool.version, url=tool.release_url)
            for tool in sorted(TOOLCHAIN, key=lambda tool: tool.name)
        ],
        documentation_url=DOCUMENTATION_URL,
        issue_url=ISSUE_URL,
    )
