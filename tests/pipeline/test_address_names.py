from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.definitions.intensity import Transport
from shared.enums.subdomain import SubdomainSource
from shared.services.scan_resolve import ResolvedScanConfig
from stages.subdomain.config import SubdomainConfig
from stages.subdomain.noise import NameRule, reverse_dns_shaped, sift
from stages.subdomain.providers import ProviderResult
from stages.subdomain.stage import SubdomainStage, _Resolution, _Wildcard

pytestmark = pytest.mark.pipeline

APEX = "tigo.com.co"
SUBFINDER = SubdomainSource.SUBFINDER.value

# shapes read off a tigo.com.co run: 33,651 subfinder names, 0 matches on gov.np, go.id, gov.cy
GENERATED = [
    "dinamic-tigo-177-252-37-237.tigo.com.co",
    "177-252-190-4.tigo.com.co",
    "10-20-30-40.dynamic.tigo.com.co",
    "ip-10-0-0-1.tigo.com.co",
    "static_190_85_12_34.tigo.com.co",
    "34.12.85.190.static.tigo.com.co",
    "103.218.51.tigo.com.co",
    "0.51.178.tigo.com.co",
    "host-200-010-001-005.tigo.com.co",
]
NAMED = [
    "tigo.com.co",
    "www1.tigo.com.co",
    "smtp2.tigo.com.co",
    "speedtest2bog3.tigo.com.co",
    "acp-3956640.tigo.com.co",
    "o1423.abmail.factura.tigo.com.co",
    "excsibogvm-e1.hcs-uc.tigo.com.co",
    "10.tigo.com.co",
    "1-2-3.tigo.com.co",
    "v1.2.3.tigo.com.co",
    "2024-01-15-10.tigo.com.co",
    "300-20-30-40.tigo.com.co",
    "1-2-3-4-5.tigo.com.co.evil.net",
]


@pytest.mark.parametrize("name", GENERATED)
def test_a_name_spelling_an_address_is_generated(name):
    assert reverse_dns_shaped(name, APEX)


@pytest.mark.parametrize("name", NAMED)
def test_a_named_host_is_not_generated(name):
    assert not reverse_dns_shaped(name, APEX)


def test_a_certificate_or_resolver_keeps_an_address_shaped_name():
    merged = {
        "177-252-190-4.tigo.com.co": {SubdomainSource.CRTNAME.value},
        "177-252-190-5.tigo.com.co": {SUBFINDER, SubdomainSource.TLSX.value},
        "177-252-190-6.tigo.com.co": {SubdomainSource.BRUTEFORCE.value},
        "177-252-190-7.tigo.com.co": {SubdomainSource.ZONE_TRANSFER.value},
        "177-252-190-8.tigo.com.co": {SUBFINDER, SubdomainSource.AMASS.value},
        "www.tigo.com.co": {SUBFINDER},
    }
    kept, dropped = sift(merged, APEX)
    assert dropped == {"177-252-190-8.tigo.com.co": NameRule.REVERSE_DNS.value}
    assert set(kept) == set(merged) - set(dropped)


class _Run:
    """The stage with its providers and resolver replaced by synthetic output."""

    def __init__(self, **cfg) -> None:
        self.written: list[str] = []
        self.resolved: list[str] = []
        self.progress: list[str] = []
        stage = SubdomainStage.__new__(SubdomainStage)
        stage.session = None
        stage.ctx = SimpleNamespace(
            target_value=APEX,
            resolved=ResolvedScanConfig(target_value=APEX, target_type="domain"),
            recorder=None,
            is_aborted=None,
        )
        stage.cfg = SubdomainConfig(passive_tools=["subfinder"], **cfg)
        stage.transport = Transport(
            tool="dnsx", rate=None, threads=30, timeout=5, retries=0
        )
        stage._prefetch_keys = dict
        stage._select_providers = lambda _cfg, _activity: []
        stage._run_providers = self._providers
        stage._wildcard_profile = lambda _domain: _Wildcard()
        stage._expand = lambda *_args: []
        stage._write_names = lambda merged: self.written.extend(merged) or len(merged)
        stage._resolve = lambda names, _wildcard=None: (
            self.resolved.extend(names) or _Resolution(submitted=len(names))
        )
        stage._persist = lambda *_args: (0, set())
        stage.emit_progress = lambda message, **_kw: self.progress.append(message)
        self.stage = stage

    @staticmethod
    def _providers(_classes, _pctx, _activity, on_result=None):
        results = [
            ProviderResult(
                source=SubdomainSource.SUBFINDER,
                subdomains={
                    "dinamic-tigo-177-252-37-237.tigo.com.co",
                    "dinamic-tigo-177-252-191-49.tigo.com.co",
                    "103.218.51.tigo.com.co",
                    "177-252-190-4.tigo.com.co",
                    "mail.tigo.com.co",
                },
            ),
            ProviderResult(
                source=SubdomainSource.CRTNAME,
                subdomains={"177-252-190-4.tigo.com.co", "correo.mail.tigo.com.co"},
            ),
        ]
        for result in results:
            on_result(result)
        return results


def test_generated_names_are_neither_stored_nor_resolved():
    run = _Run()
    result = run.stage.run()

    kept = {
        "tigo.com.co",
        "mail.tigo.com.co",
        "correo.mail.tigo.com.co",
        "177-252-190-4.tigo.com.co",
    }
    assert set(run.written) == kept
    assert set(run.resolved) == kept
    assert result.counts["dropped_reverse_dns"] == 3
    assert result.counts["subdomains"] == 4
    assert "3 address-shaped names dropped" in run.progress


def test_the_filter_can_be_switched_off():
    run = _Run(skip_address_names=False)
    result = run.stage.run()

    assert "dinamic-tigo-177-252-37-237.tigo.com.co" in run.resolved
    assert result.counts["subdomains"] == 7
    assert not any(key.startswith("dropped_") for key in result.counts)
