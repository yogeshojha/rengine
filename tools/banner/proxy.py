"""Open a TCP tunnel to one host through the scan's proxy."""

from __future__ import annotations

import base64
import socket
import ssl
from urllib.parse import SplitResult, unquote, urlsplit

from shared.utils.net import host_port

SOCKS_SCHEMES = frozenset({"socks5", "socks5h"})
HTTP_SCHEMES = frozenset({"http", "https"})
SUPPORTED_SCHEMES = SOCKS_SCHEMES | HTTP_SCHEMES

_DEFAULT_PORT = {"socks5": 1080, "socks5h": 1080, "http": 8080, "https": 443}

_SOCKS_VERSION = 5
_SOCKS_NO_AUTH = 0
_SOCKS_USERPASS = 2
_SOCKS_CONNECT = 1
_SOCKS_DOMAIN = 3
_SOCKS_IPV4 = 1
_SOCKS_IPV6 = 4

_MAX_REPLY = 8192
_OK = range(200, 300)


class ProxyError(Exception):
    """The proxy refused the connection or cannot carry it."""


def _tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


_TLS_CONTEXT = _tls_context()


def split_proxy(proxy_url: str) -> SplitResult:
    """A proxy without a scheme is a socks5 address."""
    return urlsplit(proxy_url if "://" in proxy_url else f"socks5://{proxy_url}")


def open_tunnel(proxy_url: str, host: str, port: int, timeout: float) -> socket.socket:
    """A socket already connected to host:port through the proxy."""
    parts = split_proxy(proxy_url)
    scheme = (parts.scheme or "").lower()
    if not parts.hostname:
        msg = f"unusable proxy {proxy_url!r}"
        raise ProxyError(msg)
    if scheme in SOCKS_SCHEMES:
        return _socks5_connect(parts, host, port, timeout)
    if scheme in HTTP_SCHEMES:
        return _http_connect(parts, scheme, host, port, timeout)
    msg = f"{scheme}:// is not a proxy this prober can use"
    raise ProxyError(msg)


def _dial(parts: SplitResult, scheme: str, timeout: float) -> socket.socket:
    return socket.create_connection(
        (parts.hostname, parts.port or _DEFAULT_PORT[scheme]), timeout=timeout
    )


def _credentials(parts: SplitResult) -> tuple[str, str] | None:
    if not parts.username:
        return None
    return unquote(parts.username), unquote(parts.password or "")


def _http_connect(
    parts: SplitResult, scheme: str, host: str, port: int, timeout: float
) -> socket.socket:
    sock = _dial(parts, scheme, timeout)
    try:
        if scheme == "https":
            sock = _TLS_CONTEXT.wrap_socket(sock, server_hostname=parts.hostname)
        authority = host_port(host, port)
        lines = [f"CONNECT {authority} HTTP/1.1", f"Host: {authority}"]
        credentials = _credentials(parts)
        if credentials is not None:
            raw = f"{credentials[0]}:{credentials[1]}".encode()
            lines.append("Proxy-Authorization: Basic " + base64.b64encode(raw).decode())
        sock.sendall(("\r\n".join([*lines, "", ""])).encode())
        _read_connect_reply(sock)
    except Exception:
        sock.close()
        raise
    return sock


def _read_connect_reply(sock: socket.socket) -> None:
    """Read the status line and headers without touching the tunnelled bytes."""
    buffer = b""
    while not buffer.endswith(b"\r\n\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            msg = "the proxy closed the connection before answering CONNECT"
            raise ProxyError(msg)
        buffer += chunk
        if len(buffer) > _MAX_REPLY:
            msg = "the proxy sent an oversized CONNECT reply"
            raise ProxyError(msg)
    status = buffer.split(b"\r\n", 1)[0].decode("latin-1", "replace")
    fields = status.split(" ", 2)
    code = int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else 0
    if code not in _OK:
        msg = f"the proxy refused CONNECT with {status.strip()}"
        raise ProxyError(msg)


def _socks5_connect(
    parts: SplitResult, host: str, port: int, timeout: float
) -> socket.socket:
    sock = _dial(parts, "socks5", timeout)
    try:
        credentials = _credentials(parts)
        methods = [_SOCKS_NO_AUTH] + ([_SOCKS_USERPASS] if credentials else [])
        sock.sendall(bytes([_SOCKS_VERSION, len(methods), *methods]))
        _, method = sock.recv(2)
        if method == _SOCKS_USERPASS and credentials is not None:
            user, password = (value.encode() for value in credentials)
            sock.sendall(
                bytes([1, len(user)]) + user + bytes([len(password)]) + password
            )
            if sock.recv(2)[1] != 0:
                msg = "proxy rejected the credentials"
                raise ProxyError(msg)
        elif method != _SOCKS_NO_AUTH:
            msg = "proxy offered no usable authentication method"
            raise ProxyError(msg)

        target = host.encode()
        sock.sendall(
            bytes([_SOCKS_VERSION, _SOCKS_CONNECT, 0, _SOCKS_DOMAIN, len(target)])
            + target
            + port.to_bytes(2, "big")
        )
        reply = sock.recv(4)
        if len(reply) < 4 or reply[1] != 0:  # noqa: PLR2004
            msg = "proxy refused the connection"
            raise ProxyError(msg)
        length = {_SOCKS_IPV4: 4, _SOCKS_IPV6: 16}.get(reply[3])
        if length is None:
            length = sock.recv(1)[0]
        sock.recv(length + 2)
    except Exception:
        sock.close()
        raise
    return sock
