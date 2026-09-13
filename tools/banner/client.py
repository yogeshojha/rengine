"""Connect to a listening port, read what it says, and name the service."""

from __future__ import annotations

import contextlib
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from shared.logging import get_logger
from tools.banner.proxy import (
    SUPPORTED_SCHEMES,
    ProxyError,
    open_tunnel,
    split_proxy,
)
from tools.banner.signatures import (
    GENERIC_PAYLOAD,
    PAYLOADS,
    READ_LIMIT,
    identify,
    readable,
)

logger = get_logger(__name__)


class BannerError(Exception):
    """The prober could not be configured for the requested transport."""


def unusable_proxy(proxy_url: str | None) -> str | None:
    """The reason this proxy cannot carry a banner probe, if it cannot."""
    if not proxy_url:
        return None
    scheme = split_proxy(proxy_url).scheme.lower()
    if scheme in SUPPORTED_SCHEMES:
        return None
    return (
        f"A banner probe cannot go through a {scheme} proxy. No port was fingerprinted."
    )


@dataclass(frozen=True)
class Endpoint:
    ip: str
    port: int
    service: str | None = None
    tls: bool = False


@dataclass
class Fingerprint:
    ip: str
    port: int
    tls: bool = False
    service: str | None = None
    product: str | None = None
    version: str | None = None
    banner: str | None = None

    @property
    def identified(self) -> bool:
        return bool(self.service or self.product or self.banner)


class BannerClient:
    """A bounded, thread-pooled TCP prober."""

    def __init__(
        self,
        *,
        timeout: float = 4.0,
        concurrency: int = 32,
        proxy_url: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.concurrency = max(1, concurrency)
        self.proxy_url = proxy_url
        self.proxy_warning = unusable_proxy(proxy_url)

    def probe_all(self, endpoints: list[Endpoint]) -> list[Fingerprint]:
        if not endpoints or self.proxy_warning:
            return []
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            return [f for f in pool.map(self.probe, endpoints) if f is not None]

    def probe(self, endpoint: Endpoint) -> Fingerprint | None:
        result = Fingerprint(ip=endpoint.ip, port=endpoint.port, tls=endpoint.tls)
        try:
            data, tls = self._read(endpoint)
        except (OSError, ssl.SSLError, BannerError, ProxyError, IndexError):
            return None
        result.tls = tls
        if not data:
            return None
        result.banner = readable(data)
        for key, value in identify(data, endpoint.service).items():
            setattr(result, key, value)
        return result if result.identified else None

    def _connect(self, endpoint: Endpoint) -> socket.socket:
        if self.proxy_url:
            return open_tunnel(self.proxy_url, endpoint.ip, endpoint.port, self.timeout)
        return socket.create_connection(
            (endpoint.ip, endpoint.port), timeout=self.timeout
        )

    def _read(self, endpoint: Endpoint) -> tuple[bytes, bool]:
        sock = self._connect(endpoint)
        tls = False
        try:
            sock.settimeout(self.timeout)
            if endpoint.tls:
                sock = _TLS_CONTEXT.wrap_socket(sock)
                tls = True
            data = self._recv(sock)
            if not data:
                sock.sendall(PAYLOADS.get(endpoint.service or "", GENERIC_PAYLOAD))
                data = self._recv(sock)
            return data, tls
        finally:
            with contextlib.suppress(OSError):
                sock.close()

    @staticmethod
    def _recv(sock: socket.socket) -> bytes:
        try:
            return sock.recv(READ_LIMIT)
        except (TimeoutError, OSError):
            return b""


def _tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.set_ciphers("DEFAULT@SECLEVEL=1")
    return context


_TLS_CONTEXT = _tls_context()
