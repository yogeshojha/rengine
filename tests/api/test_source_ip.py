from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from sqlmodel import select

from shared.definitions.source_ip import (
    FAILURE_LABELS,
    TRACE_URLS,
    AddressFamily,
    SourceIpFailure,
    SourceIpPhase,
    SourceIpState,
)
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.scan import ScanRead, SourceIpRecord
from shared.services import source_ip

pytestmark = pytest.mark.api

AT = datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
V4 = TRACE_URLS[AddressFamily.IPV4.value]
V6 = TRACE_URLS[AddressFamily.IPV6.value]
TRACE = "fl=12f\nh=1.1.1.1\nip={ip}\nts=1759633200.1\nvisit_scheme=https\n"


def _client_with(monkeypatch, handler):
    real = httpx.Client

    def build(**kwargs):
        kwargs.pop("proxy", None)
        return real(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(source_ip.httpx, "Client", build)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (TRACE.format(ip="203.0.113.7"), "203.0.113.7"),
        (TRACE.format(ip="2001:0db8:0000::0001"), "2001:db8::1"),
        (TRACE.format(ip="not-an-address"), None),
        ("fl=12f\nh=1.1.1.1\n", None),
        ("", None),
    ],
)
def test_the_trace_answer_is_read_from_its_ip_line(body, expected):
    assert source_ip.parse_trace(body) == expected


def test_both_families_answer(monkeypatch):
    answers = {
        V4: httpx.Response(200, text=TRACE.format(ip="203.0.113.7")),
        V6: httpx.Response(200, text=TRACE.format(ip="2001:db8::7")),
    }
    _client_with(monkeypatch, lambda request: answers[str(request.url)])

    result = source_ip.lookup(None)

    assert result == {"ipv4": "203.0.113.7", "ipv6": "2001:db8::7", "failure": None}


def test_one_family_is_enough(monkeypatch):
    def handler(request):
        if str(request.url) == V6:
            message = "no route"
            raise httpx.ConnectError(message)
        return httpx.Response(200, text=TRACE.format(ip="203.0.113.7"))

    _client_with(monkeypatch, handler)

    assert source_ip.lookup(None) == {
        "ipv4": "203.0.113.7",
        "ipv6": None,
        "failure": None,
    }


@pytest.mark.parametrize(
    ("error", "proxy", "failure"),
    [
        (httpx.ConnectTimeout("slow"), None, SourceIpFailure.TIMEOUT),
        (httpx.ConnectError("refused"), None, SourceIpFailure.UNREACHABLE),
        (httpx.ConnectError("refused"), "http://proxy:8080", SourceIpFailure.PROXY),
        (httpx.ProxyError("407"), "http://proxy:8080", SourceIpFailure.PROXY),
    ],
)
def test_a_failed_lookup_records_its_cause(monkeypatch, error, proxy, failure):
    def handler(request):
        raise error

    _client_with(monkeypatch, handler)

    result = source_ip.lookup(proxy)

    assert result == {"ipv4": None, "ipv6": None, "failure": failure.value}


def test_an_answer_without_an_address_is_no_address(monkeypatch):
    _client_with(monkeypatch, lambda _request: httpx.Response(403, text="denied"))

    assert source_ip.lookup(None)["failure"] == SourceIpFailure.NO_ADDRESS.value


def test_a_proxy_credential_never_reaches_the_record(monkeypatch):
    secret = "hunter2-proxy-password"
    proxy = f"http://scanner:{secret}@proxy.internal:3128"

    def handler(request):
        message = f"CONNECT via {proxy} refused"
        raise httpx.ProxyError(message)

    _client_with(monkeypatch, handler)

    result = source_ip.lookup(proxy)
    stored = source_ip.record(None, SourceIpPhase.START, result, proxied=True, at=AT)

    assert secret not in repr(stored)
    assert "proxy.internal" not in repr(stored)
    assert stored["checks"][0]["failure"] == SourceIpFailure.PROXY.value


def test_every_failure_has_a_label():
    assert set(FAILURE_LABELS) == {f.value for f in SourceIpFailure}


def test_three_states():
    assert source_ip.initial(True) == {
        "state": SourceIpState.MEASURED.value,
        "checks": [],
    }
    assert source_ip.initial(False) == {"state": SourceIpState.OFF.value, "checks": []}
    assert source_ip.addresses(None) == []
    assert ScanRead.model_fields["source_ip"].default is None


def test_a_check_runs_once_per_phase_and_only_when_measured():
    measured = source_ip.initial(True)
    started = source_ip.record(
        measured,
        SourceIpPhase.START,
        {"ipv4": "203.0.113.7", "ipv6": None, "failure": None},
        proxied=False,
        at=AT,
    )

    assert not source_ip.wants_check(None, SourceIpPhase.START)
    assert not source_ip.wants_check(source_ip.initial(False), SourceIpPhase.START)
    assert source_ip.wants_check(measured, SourceIpPhase.START)
    assert not source_ip.wants_check(started, SourceIpPhase.START)
    assert source_ip.wants_check(started, SourceIpPhase.END)


def test_checks_are_kept_in_phase_order_and_addresses_are_distinct():
    measured = source_ip.initial(True)
    ended = source_ip.record(
        measured,
        SourceIpPhase.END,
        {"ipv4": "198.51.100.4", "ipv6": None, "failure": None},
        proxied=True,
        at=AT,
    )
    both = source_ip.record(
        ended,
        SourceIpPhase.START,
        {"ipv4": "203.0.113.7", "ipv6": "2001:db8::7", "failure": None},
        proxied=True,
        at=AT,
    )
    again = source_ip.record(
        both,
        SourceIpPhase.END,
        {"ipv4": "203.0.113.7", "ipv6": None, "failure": None},
        proxied=True,
        at=AT,
    )

    assert [c["phase"] for c in both["checks"]] == ["start", "end"]
    assert source_ip.addresses(both) == ["203.0.113.7", "2001:db8::7", "198.51.100.4"]
    assert source_ip.addresses(again) == ["203.0.113.7", "2001:db8::7"]
    record = SourceIpRecord.model_validate(both)
    assert record.checks[1].proxied is True


async def test_the_lookups_follow_the_instance_setting(session):
    row = await session.scalar(
        select(InstanceSettings).where(InstanceSettings.singleton_key == SINGLETON_KEY)
    )
    if row is None:
        row = InstanceSettings()
        session.add(row)
    row.source_ip_lookups = True
    await session.flush()
    assert await session.run_sync(source_ip.lookups_enabled) is True

    row.source_ip_lookups = False
    await session.flush()
    assert await session.run_sync(source_ip.lookups_enabled) is False
    assert source_ip.lookups_enabled(None) is False
