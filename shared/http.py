import asyncio
import contextlib
import ipaddress
import socket
from collections.abc import Callable, Iterable
from pathlib import Path

import httpcore
import httpx

from shared.config import base_settings
from shared.utils.net import is_public_address

MAX_RETRIES = 3
CHUNK_BYTES = 1 << 20


def egress_proxy() -> str | None:
    """The proxy for outbound calls that are not scan traffic."""
    return base_settings().EGRESS_PROXY_URL or None


def _base_kwargs() -> dict:
    settings = base_settings()
    kwargs: dict = {
        "timeout": httpx.Timeout(settings.EGRESS_TIMEOUT),
        "headers": {"User-Agent": settings.EGRESS_USER_AGENT},
        "follow_redirects": True,
    }
    proxy = egress_proxy()
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


def public_addresses(host: str, port: int) -> list[str]:
    """The addresses to connect to in order, when every address the host resolves to is public."""
    refused = f"{host} resolves to an address that is not public."
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        msg = f"{host} did not resolve."
        raise httpcore.ConnectError(msg) from exc
    addresses = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            raise httpcore.ConnectError(refused) from None
    if not addresses or not all(is_public_address(a) for a in addresses):
        raise httpcore.ConnectError(refused)
    return list(dict.fromkeys(str(a) for a in addresses))


_CONNECT_FAILED = (httpcore.ConnectError, httpcore.ConnectTimeout)


class _PublicBackend(httpcore.NetworkBackend):
    def __init__(self) -> None:
        self._inner = httpcore.SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable | None = None,
    ) -> httpcore.NetworkStream:
        *earlier, last = public_addresses(host, port)
        for address in earlier:
            with contextlib.suppress(*_CONNECT_FAILED):
                return self._inner.connect_tcp(
                    address, port, timeout, local_address, socket_options
                )
        return self._inner.connect_tcp(
            last, port, timeout, local_address, socket_options
        )

    def sleep(self, seconds: float) -> None:
        self._inner.sleep(seconds)


class _AsyncPublicBackend(httpcore.AsyncNetworkBackend):
    def __init__(self) -> None:
        self._inner = httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109
        local_address: str | None = None,
        socket_options: Iterable | None = None,
    ) -> httpcore.AsyncNetworkStream:
        *earlier, last = await asyncio.to_thread(public_addresses, host, port)
        for address in earlier:
            with contextlib.suppress(*_CONNECT_FAILED):
                return await self._inner.connect_tcp(
                    address, port, timeout, local_address, socket_options
                )
        return await self._inner.connect_tcp(
            last, port, timeout, local_address, socket_options
        )

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class PublicTransport(httpx.HTTPTransport):
    """Connects only to a public address, the one it checked."""

    def __init__(self, *, retries: int = 0) -> None:
        super().__init__(retries=retries)
        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(),
            retries=retries,
            network_backend=_PublicBackend(),
        )


class AsyncPublicTransport(httpx.AsyncHTTPTransport):
    """Connects only to a public address, the one it checked."""

    def __init__(self, *, retries: int = 0) -> None:
        super().__init__(retries=retries)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(),
            retries=retries,
            network_backend=_AsyncPublicBackend(),
        )


def get_async_client(**overrides) -> httpx.AsyncClient:
    kwargs = _base_kwargs()
    kwargs["transport"] = httpx.AsyncHTTPTransport(retries=MAX_RETRIES)
    kwargs.update(overrides)
    return httpx.AsyncClient(**kwargs)


def get_sync_client(**overrides) -> httpx.Client:
    kwargs = _base_kwargs()
    kwargs["transport"] = httpx.HTTPTransport(retries=MAX_RETRIES)
    kwargs.update(overrides)
    return httpx.Client(**kwargs)


def get_public_client(*, retries: int = MAX_RETRIES, **overrides) -> httpx.Client:
    """Connects to public addresses only, or through the egress proxy when one is set."""
    kwargs = _base_kwargs()
    proxy = kwargs.pop("proxy", None)
    kwargs["follow_redirects"] = False
    kwargs["transport"] = (
        httpx.HTTPTransport(proxy=proxy, retries=retries)
        if proxy
        else PublicTransport(retries=retries)
    )
    kwargs.update(overrides)
    return httpx.Client(**kwargs)


def download(
    url: str,
    target: Path,
    *,
    timeout: float,
    max_bytes: int,
    on_chunk: Callable[[], None] | None = None,
) -> int:
    """Stream a file to disk and return its size."""
    copied = 0
    with (
        get_sync_client(timeout=timeout) as client,
        client.stream("GET", url) as response,
    ):
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_bytes(CHUNK_BYTES):
                copied += len(chunk)
                if copied > max_bytes:
                    msg = f"{target.name} exceeded {max_bytes} bytes"
                    raise ValueError(msg)
                handle.write(chunk)
                if on_chunk is not None:
                    on_chunk()
    return copied


def fetch(url: str, *, timeout: float, max_bytes: int) -> bytes:
    """The first max_bytes of a response body."""
    body = bytearray()
    with (
        get_sync_client(timeout=timeout) as client,
        client.stream("GET", url) as response,
    ):
        response.raise_for_status()
        for chunk in response.iter_bytes(CHUNK_BYTES):
            body += chunk
            if len(body) >= max_bytes:
                break
    return bytes(body[:max_bytes])
