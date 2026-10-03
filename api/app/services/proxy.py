from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.http import get_async_client
from shared.models.proxy import (
    PROXY_SCHEMES,
    Proxy,
    ProxyCreate,
    ProxyEndpoint,
    ProxyEndpointRead,
    ProxyRead,
    ProxyTestResult,
    ProxyUpdate,
)
from shared.models.scan_context import ScanContext
from shared.services import locks
from shared.services.proxy_resolve import (
    build_proxy_url as _build_url,
)
from shared.services.proxy_resolve import (
    load_proxy_endpoints as _load_endpoints,
)
from shared.services.proxy_resolve import (
    resolve_proxy_url as _resolve_proxy_url,
)
from shared.services.scan_resolve import MASK
from shared.utils.crypto import encrypt_secret
from shared.utils.datetime import utc_now
from shared.utils.net import host_port

_TEST_URL = "https://api.ipify.org"
_TEST_TIMEOUT = 8.0
_TCP_TIMEOUT = 6.0
_MIN_PORT = 1
_MAX_PORT = 65535
_MAX_TESTED = 10


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


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


def _restore_passwords(
    incoming: list[ProxyEndpoint], previous: list[ProxyEndpoint]
) -> list[ProxyEndpoint]:
    stored = {_endpoint_key(e): e.password for e in previous}
    merged: list[ProxyEndpoint] = []
    for ep in incoming:
        if MASK not in (ep.password or ""):
            merged.append(ep)
            continue
        key = _endpoint_key(ep)
        if key not in stored:
            msg = f"Enter the password again for {host_port(ep.host, ep.port)}."
            raise _bad(msg)
        merged.append(ep.model_copy(update={"password": stored[key]}))
    return merged


def _mask_url(ep: ProxyEndpoint) -> str:
    authority = host_port(ep.host, ep.port)
    if ep.username:
        cred = f"{ep.username}:{MASK}@" if ep.password else f"{ep.username}@"
        return f"{ep.scheme}://{cred}{authority}"
    return f"{ep.scheme}://{authority}"


def _endpoint_to_read(ep: ProxyEndpoint) -> ProxyEndpointRead:
    return ProxyEndpointRead(
        scheme=ep.scheme,
        host=ep.host,
        port=ep.port,
        username=ep.username,
        has_password=bool(ep.password),
        url_masked=_mask_url(ep),
    )


def _encrypt_endpoints(endpoints: list[ProxyEndpoint]) -> str:
    payload = [e.model_dump() for e in endpoints]
    return encrypt_secret(json.dumps(payload))


def _summarize(
    endpoints: list[ProxyEndpoint], results: list[ProxyTestResult]
) -> ProxyTestResult:
    if len(results) == 1:
        return results[0]
    passed = [r for r in results if r.success]
    if len(passed) == len(results):
        return ProxyTestResult(
            success=True,
            message=f"All {len(results)} endpoints carried the request.",
            latency_ms=max(r.latency_ms or 0 for r in passed),
            reachable=True,
        )
    failed = next(i for i, r in enumerate(results) if not r.success)
    ep = endpoints[failed]
    return ProxyTestResult(
        success=False,
        message=(
            f"{len(passed)} of {len(results)} endpoints carried the request. "
            f"{host_port(ep.host, ep.port)}: {results[failed].message}"
        ),
        reachable=all(r.reachable for r in results),
    )


class ProxyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def to_read(self, proxy: Proxy, contexts: int = 0) -> ProxyRead:
        endpoints = _load_endpoints(proxy)
        return ProxyRead(
            id=proxy.id,
            name=proxy.name,
            description=proxy.description,
            is_active=proxy.is_active,
            is_default=proxy.is_default,
            endpoints=[_endpoint_to_read(e) for e in endpoints],
            endpoint_count=proxy.endpoint_count,
            contexts=contexts,
            created_at=proxy.created_at,
            updated_at=proxy.updated_at,
            last_test_at=proxy.last_test_at,
            last_test_ok=proxy.last_test_ok,
            last_test_message=proxy.last_test_message,
        )

    async def _read(self, proxy: Proxy) -> ProxyRead:
        used = await self.session.scalar(
            select(func.count()).where(ScanContext.proxy_id == proxy.id)
        )
        return self.to_read(proxy, int(used or 0))

    async def list(self) -> list[ProxyRead]:
        result = await self.session.execute(
            select(Proxy).order_by(Proxy.is_default.desc(), Proxy.updated_at.desc())
        )
        used = dict(
            (
                await self.session.execute(
                    select(ScanContext.proxy_id, func.count())
                    .where(ScanContext.proxy_id.is_not(None))
                    .group_by(ScanContext.proxy_id)
                )
            ).all()
        )
        return [self.to_read(p, used.get(p.id, 0)) for p in result.scalars().all()]

    async def create(self, data: ProxyCreate, created_by: UUID) -> ProxyRead:
        _validate_endpoints(data.endpoints)
        _restore_passwords(data.endpoints, [])

        proxy = Proxy(
            name=data.name,
            description=data.description,
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
        return await self._read(proxy)

    async def update(self, id: UUID, data: ProxyUpdate) -> ProxyRead:
        proxy = await self._get_or_404(id)

        if data.name is not None:
            proxy.name = data.name
        if data.description is not None:
            proxy.description = data.description
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
        return await self._read(proxy)

    async def delete(self, id: UUID) -> None:
        proxy = await self._get_or_404(id)
        await self.session.execute(
            update(ScanContext)
            .where(ScanContext.proxy_id == proxy.id)
            .values(proxy_id=None)
        )
        await self.session.delete(proxy)
        await self.session.commit()

    async def set_default(self, id: UUID) -> ProxyRead:
        proxy = await self._get_or_404(id)
        await self._lock_defaults()
        await self._unset_other_defaults(proxy.id)
        proxy.is_default = True
        proxy.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(proxy)
        return await self._read(proxy)

    async def test(self, id: UUID) -> ProxyTestResult:
        proxy = await self._get_or_404(id)
        endpoints = _load_endpoints(proxy)
        if not endpoints:
            return await self._persist_test(
                proxy,
                ProxyTestResult(success=False, message="No endpoints configured."),
            )

        tested = endpoints[:_MAX_TESTED]
        results = await asyncio.gather(
            *(self._probe(ep, _build_url(ep)) for ep in tested)
        )
        return await self._persist_test(proxy, _summarize(tested, results))

    async def scan_proxy(self, context: ScanContext | None) -> Proxy | None:
        """The context's proxy, or the default proxy for a scan without a context."""
        if context is None:
            result = await self.session.execute(
                select(Proxy).where(
                    Proxy.is_default.is_(True), Proxy.is_active.is_(True)
                )
            )
            return result.scalars().first()
        if context.proxy_id is None:
            return None
        return await self.session.get(Proxy, context.proxy_id)

    async def scan_proxy_url(self, context: ScanContext | None) -> str | None:
        return _resolve_proxy_url(await self.scan_proxy(context))

    def _merge_endpoints(
        self, proxy: Proxy, incoming: list[ProxyEndpoint]
    ) -> list[ProxyEndpoint]:
        return _restore_passwords(incoming, _load_endpoints(proxy))

    async def _probe(self, ep: ProxyEndpoint, url: str) -> ProxyTestResult:
        start = time.monotonic()
        try:
            async with get_async_client(
                proxy=url, timeout=httpx.Timeout(_TEST_TIMEOUT)
            ) as client:
                resp = await client.get(_TEST_URL)
                resp.raise_for_status()
        except (httpx.HTTPError, ImportError, ValueError, OSError) as exc:
            return await self._tcp_probe(ep, str(exc) or exc.__class__.__name__)
        latency = int((time.monotonic() - start) * 1000)
        return ProxyTestResult(
            success=True,
            message="Proxy reachable.",
            latency_ms=latency,
            reachable=True,
        )

    async def _tcp_probe(self, ep: ProxyEndpoint, reason: str) -> ProxyTestResult:
        """The port's own reachability, after the proxied request failed."""
        try:
            conn = asyncio.open_connection(ep.host, ep.port)
            _, writer = await asyncio.wait_for(conn, timeout=_TCP_TIMEOUT)
            writer.close()
            await writer.wait_closed()
        except (TimeoutError, OSError) as exc:
            return ProxyTestResult(
                success=False, message=f"Connection failed: {exc}", latency_ms=None
            )
        return ProxyTestResult(
            success=False,
            message=(
                f"{host_port(ep.host, ep.port)} accepts connections. "
                f"The request through the proxy failed: {reason[:200]}. "
                "Check the scheme and the credentials."
            ),
            latency_ms=None,
            reachable=True,
        )

    async def _persist_test(
        self, proxy: Proxy, result: ProxyTestResult
    ) -> ProxyTestResult:
        proxy.last_test_at = utc_now()
        proxy.last_test_ok = result.success
        proxy.last_test_message = result.message
        await self.session.commit()
        return result

    async def _lock_defaults(self) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"), {"k": locks.PROXY_DEFAULT}
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
