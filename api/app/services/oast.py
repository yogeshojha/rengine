"""Read and change the instance's out-of-band settings."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import socket
import ssl
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.instance_settings import InstanceSettingsService
from shared.definitions.evidence import Evidence
from shared.definitions.oast import (
    DEFAULT_WAIT_SECONDS,
    MAX_WAIT_SECONDS,
    MIN_WAIT_SECONDS,
    PUBLIC_SERVERS,
    OastMode,
    normalize_server,
)
from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.api_key import APIKey
from shared.models.instance_settings import InstanceSettings, oast_reason
from shared.models.oast import OastRead, OastTest, OastUpdate
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import Vulnerability
from shared.utils.datetime import utc_now
from shared.utils.net import is_public_address

logger = get_logger(__name__)


def _is_certificate_error(exc: Exception) -> bool:
    seen: Exception | BaseException | None = exc
    while seen is not None:
        if isinstance(seen, ssl.SSLError):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


_PROBE_TIMEOUT = 6.0
_PROBE_PATH = "/poll"


async def instance_reason(session: AsyncSession) -> str | None:
    """Why out-of-band testing cannot be used on this instance, or None when it can."""
    return oast_reason(await session.scalar(InstanceSettings.singleton()))


class OastService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _row(self) -> InstanceSettings:
        return await InstanceSettingsService(self.session).get_or_create()

    async def read(self) -> OastRead:
        row = await self._row()
        interactions, last_interaction = await self._proven()
        return OastRead(
            mode=row.oast_mode,
            server=row.oast_host,
            wait_seconds=row.oast_wait_seconds,
            public_acknowledged=row.oast_public_acknowledged,
            token_set=await self._token_set(),
            public_servers=list(PUBLIC_SERVERS),
            checks=await self._checks(),
            reason=row.oast_off_reason,
            last_interaction_at=last_interaction,
            interactions=interactions,
        )

    async def update(self, data: OastUpdate) -> OastRead:
        row = await self._row()
        if data.mode is not None:
            row.oast_mode = data.mode
        if data.server is not None:
            server = normalize_server(data.server)
            if data.server.strip() and server is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="That is not a hostname. Use the server's domain.",
                )
            row.oast_server = server
        if data.wait_seconds is not None:
            row.oast_wait_seconds = max(
                MIN_WAIT_SECONDS, min(MAX_WAIT_SECONDS, data.wait_seconds)
            )
        if data.public_acknowledged is not None:
            row.oast_public_acknowledged = data.public_acknowledged
        if row.oast_mode == OastMode.SELF_HOSTED.value and not row.oast_host:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Set the server before choosing self-hosted.",
            )
        row.updated_at = utc_now()
        await self.session.commit()
        return await self.read()

    async def reset(self) -> OastRead:
        """Back to off: no server, no token, no acknowledgement."""
        row = await self._row()
        row.oast_mode = OastMode.OFF.value
        row.oast_server = None
        row.oast_public_acknowledged = False
        row.oast_wait_seconds = DEFAULT_WAIT_SECONDS
        row.updated_at = utc_now()
        for key in await self._keys():
            await self.session.delete(key)
        await self.session.commit()
        return await self.read()

    async def test(self) -> OastTest:
        """Ask the configured server whether it answers. Nothing is scanned."""
        row = await self._row()
        server = row.oast_host
        if row.oast_mode == OastMode.PUBLIC.value:
            server = PUBLIC_SERVERS[0]
        if not server:
            return OastTest(ok=False, detail="No server is set.")
        address, refusal = await asyncio.to_thread(self._resolve, server)
        if address is None:
            return OastTest(ok=False, detail=refusal or "No server is set.")
        return await self._probe(server, address)

    # ---------- helpers ----------

    @staticmethod
    def _resolve(host: str) -> tuple[str | None, str | None]:
        """The host's address, or the reason it may not be reached."""
        unresolved = f"{host} did not resolve. Check the domain's DNS records."
        try:
            infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except OSError:
            return None, unresolved
        addresses = []
        for info in infos:
            with contextlib.suppress(ValueError):
                addresses.append(ipaddress.ip_address(info[4][0]))
        if not addresses:
            return None, unresolved
        for parsed in addresses:
            if not is_public_address(parsed):
                return (
                    None,
                    f"{host} resolves to {parsed}, which is not a public address.",
                )
        return str(addresses[0]), None

    async def _probe(self, server: str, address: str) -> OastTest:
        url = f"https://{server}{_PROBE_PATH}"
        try:
            async with httpx.AsyncClient(
                timeout=_PROBE_TIMEOUT, follow_redirects=False, verify=True
            ) as client:
                answer = await client.get(url)
        except httpx.HTTPError as exc:
            if _is_certificate_error(exc):
                return OastTest(
                    ok=False,
                    address=address,
                    detail=f"{server} answered with a certificate this instance does not trust.",
                )
            return OastTest(
                ok=False,
                address=address,
                detail=f"{server} did not answer. Check the domain and this instance's outbound access.",
            )
        if answer.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            return OastTest(
                ok=False,
                address=address,
                status_code=answer.status_code,
                detail=f"{server} answered {answer.status_code}.",
            )
        return OastTest(
            ok=True,
            address=address,
            status_code=answer.status_code,
            detail=f"{server} answered on {address}.",
        )

    async def _keys(self) -> list[APIKey]:
        rows = await self.session.execute(
            select(APIKey).where(APIKey.provider == APIProvider.INTERACTSH)
        )
        return list(rows.scalars().all())

    async def _token_set(self) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count())
                .select_from(APIKey)
                .where(
                    APIKey.provider == APIProvider.INTERACTSH,
                    APIKey.is_enabled.is_(True),
                )
            )
        )

    async def _checks(self) -> int:
        return int(
            await self.session.scalar(
                select(func.count(VulnTemplate.id)).where(
                    VulnTemplate.enabled.is_(True),
                    VulnTemplate.needs_oast.is_(True),
                )
            )
            or 0
        )

    async def _proven(self) -> tuple[int, datetime | None]:
        """Findings a callback confirmed, and the newest. `proven` is that set by definition."""
        row = (
            await self.session.execute(
                select(
                    func.count(Vulnerability.id),
                    func.max(Vulnerability.discovered_at),
                ).where(Vulnerability.evidence == Evidence.PROVEN.value)
            )
        ).one()
        return int(row[0] or 0), row[1]
