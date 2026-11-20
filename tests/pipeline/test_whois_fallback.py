"""Port-43 WHOIS transport, proxy and fallback."""

from __future__ import annotations

import contextlib
import socket
import threading
import time

import pytest

from tools.banner.proxy import ProxyError
from tools.whois.providers import port43
from tools.whois.providers.whoisit import RDAPProviderError, RDAPUnsupportedError
from tools.whois.service import WhoisLookupError, WhoisService

pytestmark = pytest.mark.pipeline

REGISTERED = "Domain Name: example.be\nRegistrar: Example Registrar\nName Server: ns1.example.net\n"


@pytest.fixture(autouse=True)
def _fresh_referrals():
    port43.whois_server_for.cache_clear()
    port43._unreachable.clear()
    yield
    port43.whois_server_for.cache_clear()
    port43._unreachable.clear()


class _Registry:
    """A local port-43 server that records each query."""

    def __init__(self, reply, *, hold: float = 0.0) -> None:
        self.reply = reply
        self.hold = hold
        self.queries: list[str] = []
        self._server = socket.create_server(("127.0.0.1", 0))
        self._server.settimeout(5)
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            with conn:
                self.queries.append(conn.recv(1024).decode().strip())
                reply = self.reply(self.queries[-1])
                try:
                    if self.hold:
                        conn.sendall(reply[:1])
                        time.sleep(self.hold)
                    conn.sendall(reply)
                except OSError:
                    continue

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._server.shutdown(socket.SHUT_RDWR)
        self._server.close()
        self._thread.join(timeout=5)


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch):
    servers: list[_Registry] = []

    def start(reply, **kwargs) -> _Registry:
        server = _Registry(reply, **kwargs)
        servers.append(server)

        def dial(_host: str, _deadline: float) -> socket.socket:
            return socket.create_connection(("127.0.0.1", server.port), timeout=5)

        monkeypatch.setattr(port43, "_dial", dial)
        return server

    yield start
    for server in servers:
        server.close()


def _answers(query: str) -> bytes:
    if query == "be":
        return b"refer:        whois.dns.be\n"
    return REGISTERED.encode()


def test_the_registry_named_by_iana_is_asked(registry):
    server = registry(_answers)

    shape = port43.lookup_domain("example.be")

    assert server.queries == ["be", "example.be"]
    assert shape["whois_server"] == "whois.dns.be"
    assert shape["nameservers"] == ["ns1.example.net"]


def test_the_referral_is_asked_once_per_tld(registry):
    server = registry(_answers)

    port43.lookup_domain("example.be")
    port43.lookup_domain("other.be")

    assert server.queries == ["be", "example.be", "other.be"]


def test_a_registry_takes_its_own_query_form(registry):
    def answers(query: str) -> bytes:
        if query == "de":
            return b"whois:        whois.denic.de\n"
        return b"Domain: example.de\nNserver: ns1.example.net\nStatus: connect\n"

    server = registry(answers)

    port43.lookup_domain("example.de")

    assert server.queries == ["de", "-T dn,ace example.de"]


def test_a_reply_that_trickles_is_cut_at_the_deadline(registry, monkeypatch):
    monkeypatch.setattr(port43, "EXCHANGE_SECONDS", 0.3)
    registry(lambda _query: b"refer: whois.dns.be\n", hold=2.0)

    started = time.monotonic()
    with pytest.raises(port43.Port43Error, match="did not answer on port 43"):
        port43.whois_server_for("be")

    assert time.monotonic() - started < 1.5


def test_a_reply_is_capped(registry, monkeypatch):
    monkeypatch.setattr(port43, "MAX_RESPONSE_BYTES", 8192)
    registry(lambda _query: b"x" * 200_000)

    assert len(port43._query("whois.dns.be", "example.be")) < 20_000


def test_a_private_address_is_not_dialled(monkeypatch):
    def resolve(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 43))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    with pytest.raises(port43.Port43Error, match="does not resolve to a public"):
        port43._query("whois.dns.be", "example.be")


def test_a_referral_that_is_not_a_hostname_is_refused(registry):
    registry(lambda _query: b"refer:        10.0.0.5:22/x\n")

    with pytest.raises(port43.Port43Error, match="IANA lists no WHOIS server"):
        port43.whois_server_for("be")


@pytest.mark.parametrize("domain", ["example.be\r\nhelp", "example", "-h example.be"])
def test_a_query_that_is_not_a_domain_is_refused(domain: str):
    with pytest.raises(port43.Port43Error, match="is not a domain name"):
        port43.lookup_domain(domain)


def test_an_unregistered_domain_is_named(registry):
    def answers(query: str) -> bytes:
        if query == "be":
            return b"refer: whois.dns.be\n"
        return b"Domain:\texample.be\nStatus:\tAVAILABLE\n"

    registry(answers)

    with pytest.raises(port43.Port43Error, match=r"^example\.be is not registered\.$"):
        port43.lookup_domain("example.be")


def test_a_refusal_is_not_a_record(registry):
    def answers(query: str) -> bytes:
        if query == "ch":
            return b"whois: whois.nic.ch\n"
        return b"Requests of this client are not permitted. Please use https://www.nic.ch/whois/ for queries.\n"

    registry(answers)

    with pytest.raises(port43.Port43Error, match="returned no registration data"):
        port43.lookup_domain("example.ch")


def test_the_proxy_carries_both_exchanges(registry, monkeypatch):
    server = registry(_answers)
    tunnels: list[tuple] = []

    def tunnel(proxy_url, host, port, timeout, *, verify=False, deadline=None):
        tunnels.append((proxy_url, host, port, verify))
        return socket.create_connection(("127.0.0.1", server.port), timeout=timeout)

    def direct(*_args):
        pytest.fail("dialled past the proxy")

    monkeypatch.setattr(port43, "open_tunnel", tunnel)
    monkeypatch.setattr(port43, "_dial", direct)

    port43.lookup_domain("example.be", "socks5://127.0.0.1:1080")

    assert tunnels == [
        ("socks5://127.0.0.1:1080", "whois.iana.org", 43, True),
        ("socks5://127.0.0.1:1080", "whois.dns.be", 43, True),
    ]


def test_a_proxy_failure_names_no_proxy_address(monkeypatch):
    def tunnel(proxy_url, *_args, **_kwargs):
        msg = f"unusable proxy {proxy_url!r}"
        raise ProxyError(msg)

    monkeypatch.setattr(port43, "open_tunnel", tunnel)

    with pytest.raises(port43.Port43Error) as caught:
        port43.whois_server_for("be", "http://user:secret@proxy.example:8080")

    assert "secret" not in str(caught.value)
    assert "proxy.example" not in str(caught.value)


class _Rdap:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def lookup_domain(self, _domain: str):
        raise self.error


def test_the_service_falls_back_through_its_proxy(monkeypatch):
    asked: list[tuple] = []

    def lookup(domain, proxy_url=None):
        asked.append((domain, proxy_url))
        return port43.to_whoisit_shape(domain, "whois.dns.be", REGISTERED)

    monkeypatch.setattr(port43, "lookup_domain", lookup)
    service = WhoisService(proxy_url="socks5://127.0.0.1:1080")
    service._provider = _Rdap(RDAPUnsupportedError("no rdap"))

    response = service.lookup_domain("www.example.be")

    assert asked == [("example.be", "socks5://127.0.0.1:1080")]
    assert response.to_db_fields()["registrar_name"] == "Example Registrar"


def test_a_failed_fallback_states_both_facts(monkeypatch):
    def lookup(_domain, proxy_url=None):
        msg = "whois.dns.be did not answer on port 43."
        raise port43.Port43Error(msg)

    monkeypatch.setattr(port43, "lookup_domain", lookup)
    service = WhoisService()
    service._provider = _Rdap(RDAPUnsupportedError("no rdap"))

    with pytest.raises(WhoisLookupError) as caught:
        service.lookup_domain("example.be")

    assert str(caught.value) == (
        "No RDAP server for .be. whois.dns.be did not answer on port 43."
    )


def test_another_rdap_failure_does_not_fall_back(monkeypatch):
    def lookup(*_args, **_kwargs):
        pytest.fail("fell back")

    monkeypatch.setattr(port43, "lookup_domain", lookup)
    service = WhoisService()
    service._provider = _Rdap(RDAPProviderError("RDAP query failed"))

    with pytest.raises(WhoisLookupError, match="RDAP query failed"):
        service.lookup_domain("example.com")


def test_a_server_that_did_not_answer_is_not_dialled_again_at_once(monkeypatch):
    dials: list[str] = []

    def dial(server: str, _deadline: float) -> socket.socket:
        dials.append(server)
        raise TimeoutError

    monkeypatch.setattr(port43, "_dial", dial)

    for _ in range(3):
        with pytest.raises(port43.Port43Error, match="did not answer on port 43"):
            port43.whois_server_for("be")

    assert dials == ["whois.iana.org"]


def test_a_unicode_name_is_asked_for_as_its_a_label(registry):
    def answers(query: str) -> bytes:
        if query == "de":
            return b"whois: whois.denic.de\n"
        return b"Domain: xn--mnchen-3ya.de\nNserver: ns1.example.net\nStatus: connect\n"

    server = registry(answers)

    port43.lookup_domain("münchen.de")

    assert server.queries == ["de", "-T dn,ace xn--mnchen-3ya.de"]


def test_control_bytes_are_dropped_from_a_reply(registry):
    registry(lambda _query: b"Registrar: Exam\x00ple\x07 Registrar\n")

    assert (
        port43._query("whois.dns.be", "example.be") == "Registrar: Example Registrar\n"
    )


def _proxy(handler) -> tuple[socket.socket, int, threading.Thread]:
    server = socket.create_server(("127.0.0.1", 0))
    server.settimeout(5)

    def serve() -> None:
        try:
            conn, _ = server.accept()
        except OSError:
            return
        with conn, contextlib.suppress(OSError):
            handler(conn)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return server, server.getsockname()[1], thread


def test_a_socks_proxy_that_answers_short_is_a_proxy_failure():
    def handler(conn: socket.socket) -> None:
        conn.recv(16)
        conn.sendall(b"\x05")

    server, port, thread = _proxy(handler)
    try:
        with pytest.raises(port43.Port43Error, match="The proxy did not open"):
            port43.whois_server_for("be", f"socks5://127.0.0.1:{port}")
    finally:
        server.close()
        thread.join(timeout=5)


def test_a_proxy_that_trickles_its_reply_is_cut_at_the_deadline(monkeypatch):
    monkeypatch.setattr(port43, "EXCHANGE_SECONDS", 0.5)

    def handler(conn: socket.socket) -> None:
        conn.recv(1024)
        for byte in b"HTTP/1.1 200 OK\r\nX-Slow: yes":
            conn.sendall(bytes([byte]))
            time.sleep(0.2)

    server, port, thread = _proxy(handler)
    started = time.monotonic()
    try:
        with pytest.raises(port43.Port43Error, match="The proxy did not open"):
            port43.whois_server_for("be", f"http://127.0.0.1:{port}")
    finally:
        server.close()
    assert time.monotonic() - started < 2
    thread.join(timeout=10)
