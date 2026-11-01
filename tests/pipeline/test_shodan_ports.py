from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from shared.definitions.ports import (
    PASSIVE_PORT_SOURCES,
    PORT_SOURCE_LABELS,
    PortSource,
)
from shared.services.port_inventory import ServiceObservation
from stages.passive_ports import stage as stage_module
from stages.passive_ports.config import SHODAN_BUDGET_SECONDS, SHODAN_MAX_FAILURES
from stages.passive_ports.stage import PassivePortsStage
from tools.shodan import client as client_module
from tools.shodan.client import (
    ShodanClient,
    ShodanError,
    ShodanRateLimitedError,
    ShodanRefusedError,
)
from tools.shodan.parser import MAX_CPES, parse_host

pytestmark = pytest.mark.pipeline

KEY = "s3cr3t-shodan-key"

HOST = {
    "ip_str": "198.51.100.7",
    "ports": [22, 443, 161],
    "data": [
        {
            "port": 22,
            "transport": "tcp",
            "product": "OpenSSH",
            "version": "8.2p1 Ubuntu-4ubuntu0.5",
            "cpe23": ["cpe:2.3:a:openbsd:openssh:8.2"],
            "data": "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5\r\nKey type: ssh-rsa",
        },
        {"port": 443, "transport": "tcp", "data": "HTTP/1.1 200 OK", "ssl": {}},
        {
            "port": 443,
            "transport": "tcp",
            "product": "nginx",
            "ssl": {"versions": ["TLSv1.3"]},
            "data": "HTTP/1.1 200 OK\r\nServer: nginx",
        },
        {"port": 161, "transport": "udp", "product": "SNMP"},
        {"port": 0, "transport": "tcp"},
        {"port": 70000, "transport": "tcp"},
        {"port": True, "transport": "tcp"},
        "not a service",
    ],
}


# ---------- parser ----------


def test_a_host_record_becomes_one_tcp_service_per_port():
    services = {s.port: s for s in parse_host(HOST)}
    assert set(services) == {22, 443}
    ssh = services[22]
    assert (ssh.product, ssh.version) == ("OpenSSH", "8.2p1 Ubuntu-4ubuntu0.5")
    assert ssh.banner.startswith("SSH-2.0-OpenSSH_8.2p1")
    assert ssh.banner.endswith("Key type: ssh-rsa")
    assert ssh.cpe == ["cpe:2.3:a:openbsd:openssh:8.2"]
    assert not ssh.tls
    assert services[443].product == "nginx"
    assert services[443].tls


def test_values_too_long_for_their_column_are_dropped():
    (svc,) = parse_host(
        {
            "data": [
                {
                    "port": 80,
                    "product": "p" * 201,
                    "version": "v" * 101,
                    "cpe": [f"cpe:/a:x:{i}" for i in range(30)],
                    "data": "x" * 5000,
                }
            ]
        }
    )
    assert svc.product is None
    assert svc.version is None
    assert len(svc.cpe) == MAX_CPES
    assert len(svc.banner) <= 400


@pytest.mark.parametrize("payload", [None, {}, {"data": None}, {"data": "x"}, []])
def test_an_empty_or_malformed_record_has_no_services(payload):
    assert parse_host(payload) == []


# ---------- client ----------


def _client(monkeypatch, handler) -> ShodanClient:
    def fake(**overrides):
        assert overrides["follow_redirects"] is False
        return httpx.Client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(client_module, "get_sync_client", fake)
    monkeypatch.setattr(client_module, "MIN_INTERVAL", 0)
    return ShodanClient(KEY)


def test_a_lookup_sends_the_key_and_returns_the_record(monkeypatch):
    seen: list[httpx.URL] = []

    def handler(request):
        seen.append(request.url)
        return httpx.Response(200, json=HOST)

    with _client(monkeypatch, handler) as client:
        assert client.host("198.51.100.7") == HOST
    assert seen[0].path == "/shodan/host/198.51.100.7"
    assert seen[0].params["key"] == KEY


def test_an_address_shodan_never_saw_is_none(monkeypatch):
    with _client(
        monkeypatch, lambda _r: httpx.Response(404, json={"error": "No information"})
    ) as c:
        assert c.host("198.51.100.8") is None


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(401, text="<html>401</html>"), ShodanRefusedError),
        (httpx.Response(403, json={"error": "plan"}), ShodanRefusedError),
        (httpx.Response(429, json={"error": "slow down"}), ShodanRateLimitedError),
        (httpx.Response(502, text="bad gateway"), ShodanError),
        (httpx.Response(200, text="not json"), ShodanError),
        (
            httpx.Response(302, headers={"location": "https://evil.example"}),
            ShodanError,
        ),
    ],
)
def test_a_refusal_raises_without_the_key(monkeypatch, response, error):
    with (
        _client(monkeypatch, lambda _r: response) as client,
        pytest.raises(error) as exc,
    ):
        client.host("198.51.100.7")
    assert KEY not in str(exc.value)


def test_a_transport_failure_never_carries_the_url(monkeypatch):
    def handler(request):
        msg = f"cannot reach {request.url}"
        raise httpx.ConnectError(msg)

    with _client(monkeypatch, handler) as client, pytest.raises(ShodanError) as exc:
        client.host("198.51.100.7")
    assert KEY not in str(exc.value)
    assert exc.value.__cause__ is None


def test_lookups_are_paced(monkeypatch):
    clock = {"now": 100.0}
    slept: list[float] = []
    monkeypatch.setattr(client_module.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(client_module.time, "sleep", slept.append)
    monkeypatch.setattr(
        client_module,
        "get_sync_client",
        lambda **_kw: httpx.Client(
            transport=httpx.MockTransport(lambda _r: httpx.Response(404))
        ),
    )
    with ShodanClient(KEY) as client:
        client.host("198.51.100.1")
        clock["now"] += 0.25
        client.host("198.51.100.2")
    assert slept == [pytest.approx(client_module.MIN_INTERVAL - 0.25)]


# ---------- stage ----------


def _obs(ip: str, port: int) -> ServiceObservation:
    return ServiceObservation(ip=ip, port=port)


def test_the_queue_is_internetdb_addresses_most_ports_first():
    addresses = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"]
    found = [
        _obs("10.0.0.3", 80),
        _obs("10.0.0.2", 80),
        _obs("10.0.0.2", 443),
        _obs("10.0.0.4", 22),
    ]
    queue = PassivePortsStage._shodan_queue(addresses, found, internetdb_failed=False)
    assert queue == ["10.0.0.2", "10.0.0.3", "10.0.0.4"]
    assert (
        PassivePortsStage._shodan_queue(addresses, [], internetdb_failed=True)
        == addresses
    )


class _FakeClient:
    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None

    def host(self, ip: str):
        self.calls.append(ip)
        answer = self.answers.get(ip)
        if isinstance(answer, list):
            answer = answer.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def _stage(monkeypatch, client: _FakeClient) -> PassivePortsStage:
    stage = PassivePortsStage.__new__(PassivePortsStage)
    stage._check_abort = lambda: None
    stage.net_options = lambda: SimpleNamespace(proxy_url=None)
    monkeypatch.setattr(stage_module, "ShodanClient", lambda *_a, **_kw: client)
    monkeypatch.setattr(stage_module.time, "sleep", lambda _s: None)
    return stage


def test_a_pass_writes_every_service_shodan_reported(monkeypatch):
    client = _FakeClient({"198.51.100.7": HOST, "198.51.100.8": None})
    looked, services, note = _stage(monkeypatch, client)._shodan(
        KEY, ["198.51.100.7", "198.51.100.8"]
    )
    assert (looked, note) == (2, None)
    assert {(s.ip, s.port, s.product) for s in services} == {
        ("198.51.100.7", 22, "OpenSSH"),
        ("198.51.100.7", 443, "nginx"),
    }


def test_a_refused_key_stops_the_pass(monkeypatch):
    client = _FakeClient(
        {"a": ShodanRefusedError("Shodan refused the key for host lookups: HTTP 401.")}
    )
    looked, services, note = _stage(monkeypatch, client)._shodan(KEY, ["a", "b"])
    assert (looked, services) == (0, [])
    assert client.calls == ["a"]
    assert (
        note
        == "Shodan refused the key for host lookups: HTTP 401. Indexed banners not read."
    )


def test_a_rate_limit_is_retried_once(monkeypatch):
    client = _FakeClient(
        {"a": [ShodanRateLimitedError("Shodan rate limit reached."), HOST]}
    )
    looked, services, note = _stage(monkeypatch, client)._shodan(KEY, ["a"])
    assert (looked, note) == (1, None)
    assert client.calls == ["a", "a"]
    assert services


def test_repeated_failures_stop_the_pass(monkeypatch):
    error = ShodanError("Shodan returned HTTP 502.")
    client = _FakeClient(dict.fromkeys("abcde", error))
    looked, _services, note = _stage(monkeypatch, client)._shodan(KEY, list("abcde"))
    assert looked == 0
    assert len(client.calls) == SHODAN_MAX_FAILURES
    assert note.startswith(
        f"Shodan lookups stopped after {SHODAN_MAX_FAILURES} failed requests."
    )


def test_one_failure_between_answers_does_not_stop_the_pass(monkeypatch):
    client = _FakeClient(
        {"a": ShodanError("x"), "b": None, "c": ShodanError("x"), "d": None}
    )
    looked, _services, note = _stage(monkeypatch, client)._shodan(KEY, list("abcd"))
    assert (looked, note) == (2, None)


def test_the_pass_stops_at_its_budget(monkeypatch):
    clock = {"now": 0.0}

    def tick():
        clock["now"] += SHODAN_BUDGET_SECONDS / 2.5
        return clock["now"]

    monkeypatch.setattr(stage_module.time, "monotonic", tick)
    client = _FakeClient({})
    looked, _services, note = _stage(monkeypatch, client)._shodan(KEY, list("abcdef"))
    assert looked == len(client.calls) < 6
    assert note == (
        f"Shodan lookups stopped at the {SHODAN_BUDGET_SECONDS // 60}-minute budget: "
        f"{looked} of 6 addresses looked up."
    )


def test_shodan_rows_count_as_passive():
    assert PortSource.SHODAN.value in PASSIVE_PORT_SOURCES
    assert PortSource.INTERNETDB.value in PASSIVE_PORT_SOURCES
    assert PortSource.NAABU.value not in PASSIVE_PORT_SOURCES
    assert PORT_SOURCE_LABELS[PortSource.SHODAN.value] == "Shodan"


def test_the_stage_declares_the_key_it_reads():
    assert PassivePortsStage.api_keys == ("shodan",)


def test_the_shodan_client_takes_no_scan_proxy(monkeypatch):
    seen: dict = {}

    def fake(**overrides):
        seen.update(overrides)
        return httpx.Client(
            transport=httpx.MockTransport(lambda _r: httpx.Response(404))
        )

    monkeypatch.setattr(client_module, "get_sync_client", fake)
    with ShodanClient(KEY):
        pass
    assert "proxy" not in seen
