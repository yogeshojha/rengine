from __future__ import annotations

import contextlib
import socket
import threading
from collections.abc import Iterator

import pytest

from tools.banner.client import unusable_proxy
from tools.banner.proxy import ProxyError, open_tunnel, split_proxy

pytestmark = pytest.mark.pipeline

_BANNER = b"SSH-2.0-OpenSSH_9.6\r\n"
_TIMEOUT = 5.0


class _ConnectProxy:
    """A proxy that answers CONNECT and then serves a banner down the tunnel."""

    def __init__(self, reply: bytes = b"HTTP/1.1 200 Connection established\r\n\r\n"):
        self.reply = reply
        self.request = b""
        self._server = socket.socket()
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def _serve(self) -> None:
        conn, _ = self._server.accept()
        with conn:
            conn.settimeout(_TIMEOUT)
            while not self.request.endswith(b"\r\n\r\n"):
                chunk = conn.recv(1024)
                if not chunk:
                    return
                self.request += chunk
            conn.sendall(self.reply)
            if self.reply.startswith(b"HTTP/1.1 2"):
                with contextlib.suppress(OSError):
                    conn.sendall(_BANNER)
                    conn.recv(1)

    def __enter__(self) -> _ConnectProxy:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._server.close()


@pytest.fixture
def proxy() -> Iterator[_ConnectProxy]:
    with _ConnectProxy() as running:
        yield running


def test_a_http_proxy_carries_the_probe(proxy: _ConnectProxy):
    sock = open_tunnel(f"http://127.0.0.1:{proxy.port}", "10.0.0.5", 22, _TIMEOUT)
    with sock:
        sock.settimeout(_TIMEOUT)
        assert sock.recv(len(_BANNER)) == _BANNER
    assert proxy.request.startswith(b"CONNECT 10.0.0.5:22 HTTP/1.1")


def test_an_ipv6_target_is_bracketed(proxy: _ConnectProxy):
    with open_tunnel(f"http://127.0.0.1:{proxy.port}", "2001:db8::1", 443, _TIMEOUT):
        pass
    assert proxy.request.startswith(b"CONNECT [2001:db8::1]:443 HTTP/1.1")


def test_proxy_credentials_are_sent(proxy: _ConnectProxy):
    with open_tunnel(
        f"http://user:p%40ss@127.0.0.1:{proxy.port}", "10.0.0.5", 22, _TIMEOUT
    ):
        pass
    assert b"Proxy-Authorization: Basic dXNlcjpwQHNz\r\n" in proxy.request


def test_a_refused_tunnel_is_an_error():
    refusal = b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n"
    with (
        _ConnectProxy(reply=refusal) as p,
        pytest.raises(ProxyError, match="407"),
    ):
        open_tunnel(f"http://127.0.0.1:{p.port}", "10.0.0.5", 22, _TIMEOUT)


def test_a_scheme_the_prober_cannot_use_is_refused():
    with pytest.raises(ProxyError, match="ftp"):
        open_tunnel("ftp://127.0.0.1:21", "10.0.0.5", 22, _TIMEOUT)


@pytest.mark.parametrize(
    "proxy_url",
    [
        "socks5://127.0.0.1:1080",
        "http://127.0.0.1:8080",
        "https://p:8443",
        "1.2.3.4:1080",
    ],
)
def test_a_usable_proxy_raises_no_warning(proxy_url: str):
    assert unusable_proxy(proxy_url) is None


def test_an_unusable_proxy_is_named():
    assert "ftp" in (unusable_proxy("ftp://127.0.0.1:21") or "")
    assert unusable_proxy(None) is None


@pytest.mark.parametrize(
    "proxy_url", ["myproxy.internal:1080", "1.2.3.4:1080", "10.0.0.1"]
)
def test_a_bare_address_is_read_as_socks5_by_both_checks(proxy_url: str):
    assert split_proxy(proxy_url).scheme == "socks5"
    assert unusable_proxy(proxy_url) is None
