"""Connect to a listening port, read what it says, and name the service."""

from __future__ import annotations

import contextlib
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlsplit

from shared.logging import get_logger
from tools.banner.signatures import (
    GENERIC_PAYLOAD,
    PAYLOADS,
    READ_LIMIT,
    identify,
    readable,
)

logger = get_logger(__name__)

_SOCKS_VERSION = 5
_SOCKS_NO_AUTH = 0
_SOCKS_USERPASS = 2
_SOCKS_CONNECT = 1
_SOCKS_DOMAIN = 3
_SOCKS_IPV4 = 1
_SOCKS_IPV6 = 4


class BannerError(Exception):
    """The prober could not be configured for the requested transport."""


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


def _socks5_connect(proxy: str, host: str, port: int, timeout: float) -> socket.socket:
    parts = urlsplit(proxy if "://" in proxy else f"socks5://{proxy}")
    if not parts.hostname:
        msg = f"unusable proxy {proxy!r}"
        raise BannerError(msg)
    sock = socket.create_connection(
        (parts.hostname, parts.port or 1080), timeout=timeout
    )
    try:
        methods = [_SOCKS_NO_AUTH] + ([_SOCKS_USERPASS] if parts.username else [])
        sock.sendall(bytes([_SOCKS_VERSION, len(methods), *methods]))
        _, method = sock.recv(2)
        if method == _SOCKS_USERPASS:
            user = (parts.username or "").encode()
            password = (parts.password or "").encode()
            sock.sendall(
                bytes([1, len(user)]) + user + bytes([len(password)]) + password
            )
            if sock.recv(2)[1] != 0:
                msg = "proxy rejected the credentials"
                raise BannerError(msg)
        elif method != _SOCKS_NO_AUTH:
            msg = "proxy offered no usable authentication method"
            raise BannerError(msg)

        target = host.encode()
        sock.sendall(
            bytes([_SOCKS_VERSION, _SOCKS_CONNECT, 0, _SOCKS_DOMAIN, len(target)])
            + target
            + port.to_bytes(2, "big")
        )
        reply = sock.recv(4)
        if len(reply) < 4 or reply[1] != 0:  # noqa: PLR2004
            msg = "proxy refused the connection"
            raise BannerError(msg)
        length = {_SOCKS_IPV4: 4, _SOCKS_IPV6: 16}.get(reply[3])
        if length is None:
            length = sock.recv(1)[0]
        sock.recv(length + 2)
    except Exception:
        sock.close()
        raise
    return sock


class BannerClient:
    """A bounded, thread-pooled TCP prober. Sends one short probe per port."""

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

    def probe_all(self, endpoints: list[Endpoint]) -> list[Fingerprint]:
        if not endpoints:
            return []
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            return [f for f in pool.map(self.probe, endpoints) if f is not None]

    def probe(self, endpoint: Endpoint) -> Fingerprint | None:
        result = Fingerprint(ip=endpoint.ip, port=endpoint.port, tls=endpoint.tls)
        try:
            data, tls = self._read(endpoint)
        except (OSError, ssl.SSLError, BannerError, IndexError):
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
            return _socks5_connect(
                self.proxy_url, endpoint.ip, endpoint.port, self.timeout
            )
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
