from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret, try_decrypt
from shared.http import get_async_client
from shared.models.proxy import (
    PROXY_MODES,
    PROXY_SCHEMES,
    Proxy,
    ProxyCreate,
    ProxyEndpoint,
    ProxyEndpointRead,
    ProxyRead,
    ProxyTestResult,
    ProxyUpdate,
)
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now

_TEST_URL = "https://api.ipify.org"
_TEST_TIMEOUT = 8.0
_TCP_TIMEOUT = 6.0
_MIN_PORT = 1
_MAX_PORT = 65535
_DEFAULT_LOCK_KEY = 0x70726F78


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_mode(mode: str) -> None:
    if mode not in PROXY_MODES:
        msg = f"Invalid mode. Must be one of {', '.join(PROXY_MODES)}."
        raise _bad(msg)


def _validate_endpoints(endpoints: list[ProxyEndpoint]) -> None:
    if not endpoints:
        msg = "At least one endpoint is required."
        raise _bad(msg)
    for ep in endpoints:
        if ep.scheme not in PROXY_SCHEMES:
            msg = f"Invalid scheme '{ep.scheme}'. Must be one of {', '.join(PROXY_SCHEMES)}."
            raise _bad(msg)
        if not ep.host:
            msg = "Endpoint host is required."
            raise _bad(msg)
        if not (_MIN_PORT <= ep.port <= _MAX_PORT):
            msg = (
                f"Invalid port {ep.port}. Must be between {_MIN_PORT} and {_MAX_PORT}."
            )
            raise _bad(msg)


def _endpoint_key(ep: ProxyEndpoint) -> tuple:
    return (ep.scheme, ep.host, ep.port, ep.username)


def _mask_url(ep: ProxyEndpoint) -> str:
    if ep.username:
        cred = f"{ep.username}:{MASK}@" if ep.password else f"{ep.username}@"
        return f"{ep.scheme}://{cred}{ep.host}:{ep.port}"
    return f"{ep.scheme}://{ep.host}:{ep.port}"


def _endpoint_to_read(ep: ProxyEndpoint) -> ProxyEndpointRead:
    return ProxyEndpointRead(
        scheme=ep.scheme,
        host=ep.host,
        port=ep.port,
        username=ep.username,
        has_password=bool(ep.password),
        url_masked=_mask_url(ep),
    )


def _build_url(ep: ProxyEndpoint) -> str:
    if ep.username:
        cred = f"{ep.username}:{ep.password}@" if ep.password else f"{ep.username}@"
        return f"{ep.scheme}://{cred}{ep.host}:{ep.port}"
    return f"{ep.scheme}://{ep.host}:{ep.port}"


def _load_endpoints(proxy: Proxy) -> list[ProxyEndpoint]:
    raw = try_decrypt(proxy.endpoints_encrypted)
    if not raw:
        return []
    return [ProxyEndpoint(**e) for e in json.loads(raw)]


def _encrypt_endpoints(endpoints: list[ProxyEndpoint]) -> str:
    payload = [e.model_dump() for e in endpoints]
    return encrypt_secret(json.dumps(payload))


class ProxyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def to_read(self, proxy: Proxy) -> ProxyRead:
        endpoints = _load_endpoints(proxy)
        return ProxyRead(
            id=proxy.id,
            name=proxy.name,
            description=proxy.description,
            mode=proxy.mode,
            is_active=proxy.is_active,
            is_default=proxy.is_default,
            endpoints=[_endpoint_to_read(e) for e in endpoints],
            endpoint_count=proxy.endpoint_count,
            created_at=proxy.created_at,
            updated_at=proxy.updated_at,
            last_test_at=proxy.last_test_at,
            last_test_ok=proxy.last_test_ok,
            last_test_message=proxy.last_test_message,
        )

    async def list(self) -> list[ProxyRead]:
        result = await self.session.execute(
            select(Proxy).order_by(Proxy.is_default.desc(), Proxy.updated_at.desc())
        )
        return [self.to_read(p) for p in result.scalars().all()]

    async def get(self, id: UUID) -> ProxyRead:
        proxy = await self._get_or_404(id)
        return self.to_read(proxy)

    async def create(self, data: ProxyCreate, created_by: UUID) -> ProxyRead:
        _validate_mode(data.mode)
        _validate_endpoints(data.endpoints)

        proxy = Proxy(
            name=data.name,
            description=data.description,
            mode=data.mode,
            is_active=data.is_active,
            is_default=data.is_default,
            endpoints_encrypted=_encrypt_endpoints(data.endpoints),
            endpoint_count=len(data.endpoints),
            created_by=created_by,
        )
        self.session.add(proxy)
        if proxy.is_default:
            await self._lock_defaults()
            await self._unset_other_defaults(proxy.id)
        await self.session.commit()
        await self.session.refresh(proxy)
        return self.to_read(proxy)

    async def update(self, id: UUID, data: ProxyUpdate) -> ProxyRead:
        proxy = await self._get_or_404(id)

        if data.name is not None:
            proxy.name = data.name
        if data.description is not None:
            proxy.description = data.description
        if data.mode is not None:
            _validate_mode(data.mode)
            proxy.mode = data.mode
        if data.is_active is not None:
            proxy.is_active = data.is_active

        if data.endpoints is not None:
            _validate_endpoints(data.endpoints)
            merged = self._merge_endpoints(proxy, data.endpoints)
            proxy.endpoints_encrypted = _encrypt_endpoints(merged)
            proxy.endpoint_count = len(merged)

        if data.is_default is not None:
            proxy.is_default = data.is_default

        proxy.updated_at = utc_now()
        if data.is_default:
            await self._lock_defaults()
            await self._unset_other_defaults(proxy.id)
        await self.session.commit()
        await self.session.refresh(proxy)
        return self.to_read(proxy)

    async def delete(self, id: UUID) -> bool:
        proxy = await self._get_or_404(id)
        await self.session.delete(proxy)
        await self.session.commit()
        return True

    async def set_default(self, id: UUID) -> ProxyRead:
        proxy = await self._get_or_404(id)
        await self._lock_defaults()
        await self._unset_other_defaults(proxy.id)
        proxy.is_default = True
        proxy.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(proxy)
        return self.to_read(proxy)

    async def test(self, id: UUID) -> ProxyTestResult:
        proxy = await self._get_or_404(id)
        endpoints = _load_endpoints(proxy)
        if not endpoints:
            return await self._persist_test(
                proxy, False, "No endpoints configured.", None
            )

        ep = endpoints[0]
        url = _build_url(ep)
        result = await self._probe(ep, url)
        return await self._persist_test(
            proxy, result.success, result.message, result.latency_ms
        )

    async def resolve_proxy_url(self, proxy_id: UUID) -> str | None:
        proxy = await self.session.get(Proxy, proxy_id)
        if proxy is None or not proxy.is_active:
            return None
        endpoints = _load_endpoints(proxy)
        if not endpoints:
            return None
        return _build_url(endpoints[0])

    def _merge_endpoints(
        self, proxy: Proxy, incoming: list[ProxyEndpoint]
    ) -> list[ProxyEndpoint]:
        stored = {_endpoint_key(e): e.password for e in _load_endpoints(proxy)}
        merged: list[ProxyEndpoint] = []
        for ep in incoming:
            if ep.password == MASK:
                prev = stored.get(_endpoint_key(ep))
                merged.append(ep.model_copy(update={"password": prev}))
            else:
                merged.append(ep)
        return merged

    async def _probe(self, ep: ProxyEndpoint, url: str) -> ProxyTestResult:
        start = time.monotonic()
        try:
            async with get_async_client(
                proxy=url, timeout=httpx.Timeout(_TEST_TIMEOUT)
            ) as client:
                resp = await client.get(_TEST_URL)
                resp.raise_for_status()
        except (httpx.HTTPError, ImportError, ValueError, OSError):
            return await self._tcp_probe(ep)
        latency = int((time.monotonic() - start) * 1000)
        return ProxyTestResult(
            success=True, message="Proxy reachable.", latency_ms=latency
        )

    async def _tcp_probe(self, ep: ProxyEndpoint) -> ProxyTestResult:
        start = time.monotonic()
        try:
            conn = asyncio.open_connection(ep.host, ep.port)
            _, writer = await asyncio.wait_for(conn, timeout=_TCP_TIMEOUT)
            writer.close()
            await writer.wait_closed()
        except (TimeoutError, OSError) as exc:
            return ProxyTestResult(
                success=False, message=f"Connection failed: {exc}", latency_ms=None
            )
        latency = int((time.monotonic() - start) * 1000)
        return ProxyTestResult(
            success=True, message="TCP connect succeeded.", latency_ms=latency
        )

    async def _persist_test(
        self, proxy: Proxy, ok: bool, message: str, latency_ms: int | None
    ) -> ProxyTestResult:
        proxy.last_test_at = utc_now()
        proxy.last_test_ok = ok
        proxy.last_test_message = message
        await self.session.commit()
        return ProxyTestResult(success=ok, message=message, latency_ms=latency_ms)

    async def _lock_defaults(self) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"), {"k": _DEFAULT_LOCK_KEY}
        )

    async def _unset_other_defaults(self, keep_id: UUID) -> None:
        await self.session.execute(
            update(Proxy)
            .where(Proxy.id != keep_id, Proxy.is_default.is_(True))
            .values(is_default=False)
        )

    async def _get_or_404(self, id: UUID) -> Proxy:
        result = await self.session.execute(select(Proxy).where(Proxy.id == id))
        proxy = result.scalar_one_or_none()
        if not proxy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found"
            )
        return proxy
