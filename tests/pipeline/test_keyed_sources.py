from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
import yaml

from shared.definitions.api_keys import (
    API_PROVIDER_META,
    SUBFINDER_SOURCES,
    account_error,
    account_value,
    clean_meta,
    key_error,
    subfinder_value,
)
from shared.definitions.discovery_sources import (
    NOTE_KEY,
    SOURCES_KEY,
    UNKEYED_KEY,
    SourceStatus,
)
from shared.definitions.intensity import Transport
from shared.enums.api_key import APIProvider
from shared.enums.subdomain import SubdomainSource
from shared.services.scan_resolve import ResolvedScanConfig
from stages.subdomain.config import SubdomainConfig, tool_timeout
from stages.subdomain.providers import ProviderContext, ProviderResult
from stages.subdomain.providers import base as provider_base
from stages.subdomain.providers.base import SourceStat
from stages.subdomain.providers.ctfr import CtfrProvider
from stages.subdomain.providers.netlas import NetlasProvider
from stages.subdomain.providers.subfinder import (
    SubfinderProvider,
    max_time_minutes,
    parse_stats,
    record_sources,
)
from stages.subdomain.sources import run_notes, source_report
from stages.subdomain.stage import SubdomainStage, _Resolution, _Wildcard
from tools.runner.models import ToolResult

pytestmark = pytest.mark.pipeline

# `subfinder -ls` on v2.16.0, the version worker/Dockerfile pins: sources that take a key
SUBFINDER_KEYED = {
    "alienvault", "bevigil", "bufferover", "builtwith", "c99", "censys", "certspotter",
    "chaos", "chinaz", "digitalyama", "dnsdb", "dnsdumpster", "dnsrepo", "domainsproject",
    "driftnet", "fofa", "fullhunt", "github", "intelx", "leakix", "merklemap", "netlas",
    "onyphe", "profundis", "pugrecon", "quake", "redhuntlabs", "robtex", "rsecloud",
    "securitytrails", "shodan", "threatbook", "urlscan", "virustotal", "whoisxmlapi",
    "windvane", "zoomeyeapi",
}  # fmt: skip

# stderr of `subfinder -stats` on v2.16.0, colour codes included
STATS = (
    "\x1b[34m[INF]\x1b[0m Found 28 subdomains for hackerone.com in 31 seconds\n"
    "\n Source               Duration      Results   Requests     Errors\n"
    "────────────────────────────────────────────────────────────────────\n"
    " anubis               1.127s              5          1          0\n"
    " commoncrawl          10.925s             0          2          1\n"
    " virustotal           0s                  0          1          1\n"
    " rapiddns             1m2.5s             10          1          0\n"
    "\n\n The following sources were included but skipped...\n\n"
    " alienvault\n bevigil\n zoomeyeapi\n\n"
)


# ---------- key definitions ----------


def test_every_keyed_source_is_one_subfinder_reads():
    assert {spec.name for spec in SUBFINDER_SOURCES.values()} <= SUBFINDER_KEYED


def test_every_provider_names_a_group_and_a_docs_link():
    for meta in API_PROVIDER_META.values():
        assert meta["group"]
        assert meta["docs_url"].startswith("https://")


@pytest.mark.parametrize(
    ("provider", "key", "meta", "expected"),
    [
        (APIProvider.VIRUSTOTAL, "vt", None, "vt"),
        (APIProvider.CENSYS, "pat", None, "pat"),
        (
            APIProvider.CENSYS,
            "pat",
            {"organization_id": "1d8f0c2a-0000-4000-8000-000000000001"},
            "pat:1d8f0c2a-0000-4000-8000-000000000001",
        ),
        (APIProvider.FOFA, "k", {"email": "a@b.co"}, "a@b.co:k"),
        (APIProvider.FOFA, "k", None, None),
        (APIProvider.INTELX, "k", None, "free.intelx.io:k"),
        (APIProvider.INTELX, "k", {"host": "2.intelx.io"}, "2.intelx.io:k"),
        (APIProvider.ZOOMEYE, "k", {"host": "  "}, "zoomeye.ai:k"),
        (APIProvider.ZOOMEYE, "k", {"host": "zoomeye.hk"}, "zoomeye.hk:k"),
        (APIProvider.NETLAS, "k", None, None),
        (APIProvider.VIRUSTOTAL, "", None, None),
    ],
)
def test_the_subfinder_entry_for_a_key(provider, key, meta, expected):
    assert subfinder_value(provider, key, meta) == expected


@pytest.mark.parametrize(
    ("provider", "key", "problem"),
    [
        (APIProvider.VIRUSTOTAL, "", "empty"),
        (APIProvider.VIRUSTOTAL, "ab cd", "spaces"),
        (APIProvider.VIRUSTOTAL, "abc\n- injected", "spaces"),
        (APIProvider.VIRUSTOTAL, "abc\x00", "control"),
        (APIProvider.FOFA, "a:b", "colon"),
        (APIProvider.CENSYS, "pat:org", "colon"),
    ],
)
def test_a_key_that_cannot_be_stored(provider, key, problem):
    assert problem in key_error(provider, key)


@pytest.mark.parametrize(
    ("provider", "key"),
    [
        (APIProvider.TELEGRAM, "123456:AAE-token_value"),
        (APIProvider.VIRUSTOTAL, "a1b2c3"),
        (APIProvider.SHODAN, "x" * 32),
    ],
)
def test_a_key_that_can_be_stored(provider, key):
    assert key_error(provider, key) is None


@pytest.mark.parametrize(
    ("provider", "meta", "problem"),
    [
        (APIProvider.HACKERONE, None, "requires the username"),
        (APIProvider.FOFA, {"email": ""}, "requires the account email"),
        (APIProvider.FOFA, {"email": "not-an-email"}, "not an email"),
        (APIProvider.FOFA, {"email": "a:b@c.io"}, "not an email"),
        (APIProvider.INTELX, {"host": "attacker.example"}, "intelx.io host"),
        (APIProvider.INTELX, {"host": "intelx.io.attacker.example"}, "intelx.io host"),
        (APIProvider.ZOOMEYE, {"host": "zoomeye.org"}, "zoomeye.ai or zoomeye.hk"),
        (APIProvider.CENSYS, {"organization_id": "12345"}, "UUID"),
        (APIProvider.HACKERONE, {"username": "two words"}, "spaces"),
    ],
)
def test_an_account_value_that_cannot_be_stored(provider, meta, problem):
    assert problem in account_error(provider, meta)


@pytest.mark.parametrize(
    ("provider", "meta"),
    [
        (APIProvider.CENSYS, None),
        (APIProvider.INTELX, {"host": ""}),
        (APIProvider.INTELX, {"host": "free.intelx.io"}),
        (APIProvider.FOFA, {"email": "ops@example.com"}),
        (APIProvider.VIRUSTOTAL, {"anything": "ignored"}),
    ],
)
def test_an_account_value_that_can_be_stored(provider, meta):
    assert account_error(provider, meta) is None


def test_only_the_account_field_is_stored():
    assert clean_meta(APIProvider.FOFA, {"email": " a@b.co ", "x": 1}) == {
        "email": "a@b.co"
    }
    assert clean_meta(APIProvider.FOFA, {"email": "  "}) is None
    assert clean_meta(APIProvider.VIRUSTOTAL, {"username": "x"}) is None
    assert account_value(APIProvider.INTELX, None) == "free.intelx.io"


# ---------- subfinder ----------


def _ctx(**kw) -> ProviderContext:
    base = {
        "domain": "example.com",
        "timeout": 360,
        "threads": 10,
        "proxy_url": None,
        "api_keys": {},
    }
    return ProviderContext(**{**base, **kw})


@pytest.mark.parametrize(
    ("timeout", "minutes"), [(30, 1), (120, 1), (240, 3), (360, 5), (600, 9)]
)
def test_subfinder_stops_itself_before_the_process_timeout(timeout, minutes):
    assert max_time_minutes(timeout) == minutes
    assert minutes * 60 < timeout or timeout < 120


def test_every_intensity_leaves_subfinder_a_minute_to_write():
    for intensity in ("passive", "normal", "aggressive"):
        timeout = tool_timeout(intensity)
        assert timeout - max_time_minutes(timeout) * 60 >= 60


def test_the_stats_table_is_read_with_its_skipped_list():
    stats = parse_stats(STATS)
    assert stats["anubis"] == SourceStat(results=5, requests=1, errors=0)
    assert stats["virustotal"] == SourceStat(results=0, requests=1, errors=1)
    assert stats["rapiddns"].results == 10
    assert stats["zoomeyeapi"].skipped
    assert "Source" not in stats
    assert parse_stats("") == {}


def test_a_record_names_every_source():
    assert record_sources({"host": "a", "sources": ["crtsh", "thc"]}) == [
        "crtsh",
        "thc",
    ]
    assert record_sources({"host": "a", "source": "crtsh"}) == ["crtsh"]
    assert record_sources({"host": "a"}) == []


def test_the_provider_config_carries_each_stored_key():
    provider = SubfinderProvider(
        _ctx(
            api_keys={"virustotal": "vt", "fofa": "fk", "intelx": "ik", "netlas": "nk"},
            key_meta={"fofa": {"email": "a@b.co"}},
        )
    )
    config = provider.provider_config()
    assert config == {
        "virustotal": ["vt"],
        "fofa": ["a@b.co:fk"],
        "intelx": ["free.intelx.io:ik"],
    }
    assert provider._keyed == {
        "virustotal": "virustotal",
        "fofa": "fofa",
        "intelx": "intelx",
    }


def test_a_key_with_yaml_syntax_cannot_inject_config():
    hostile = 'k"\n  - other\nshodan: [x] # '
    provider = SubfinderProvider(_ctx(api_keys={"virustotal": hostile}))
    path = provider._write_provider_config()
    try:
        text = Path(path).read_text()
        assert yaml.safe_load(text) == json.loads(text) == {"virustotal": [hostile]}
    finally:
        Path(path).unlink()


def test_no_keys_writes_no_config():
    assert SubfinderProvider(_ctx())._write_provider_config() is None


class _Runner:
    calls: ClassVar[list[dict]] = []
    result: ToolResult

    def __init__(self, *_a, **_kw) -> None:
        pass

    def run(self, **kw) -> ToolResult:
        type(self).calls.append(kw)
        args = kw["args"]
        path = (
            args[args.index("-provider-config") + 1]
            if "-provider-config" in args
            else None
        )
        kw["config"] = Path(path).read_text() if path else None
        return type(self).result


def _discover(monkeypatch, result: ToolResult, **ctx) -> ProviderResult:
    _Runner.calls = []
    _Runner.result = result
    monkeypatch.setattr("stages.subdomain.providers.subfinder.CLIToolRunner", _Runner)
    monkeypatch.setattr(
        "stages.subdomain.providers.base.shutil.which", lambda *_a, **_kw: "/bin/true"
    )
    return SubfinderProvider(_ctx(**ctx)).run()


def test_subfinder_runs_with_sources_stats_and_a_deadline(monkeypatch):
    result = _discover(
        monkeypatch,
        ToolResult(
            success=True,
            exit_code=0,
            stderr=STATS,
            duration_seconds=31.0,
            json_records=[
                {"host": "a.example.com", "sources": ["anubis", "virustotal"]},
                {"host": "b.example.com", "sources": ["anubis"]},
                {"host": "", "sources": ["x"]},
            ],
        ),
        api_keys={"virustotal": "vt"},
    )
    args = _Runner.calls[0]["args"]
    assert {"-all", "-cs", "-stats"} <= set(args)
    assert args[args.index("-max-time") + 1] == "5"
    assert _Runner.calls[0]["silent"] is False
    assert json.loads(_Runner.calls[0]["config"]) == {"virustotal": ["vt"]}
    assert result.subdomains == {"a.example.com", "b.example.com"}
    assert result.breakdown == {
        "anubis": {"a.example.com", "b.example.com"},
        "virustotal": {"a.example.com"},
    }
    assert result.source_stats["virustotal"].errors == 1
    assert result.keyed_sources == {"virustotal": "virustotal"}
    assert not result.cut_short


def test_subfinder_at_its_deadline_is_cut_short(monkeypatch):
    result = _discover(
        monkeypatch,
        ToolResult(
            success=True,
            exit_code=0,
            duration_seconds=300.4,
            json_records=[{"host": "a.example.com", "sources": ["anubis"]}],
        ),
    )
    assert result.cut_short
    assert result.note == "stopped at its 5-minute budget"
    assert run_notes([result]) == "Subfinder stopped at its 5-minute budget."


def test_a_failed_run_keeps_the_keys_it_was_given(monkeypatch):
    result = _discover(
        monkeypatch,
        ToolResult(success=False, exit_code=2, error="subfinder exited with code 2"),
        api_keys={"shodan": "sk"},
    )
    assert result.error
    assert result.keyed_sources == {"shodan": "shodan"}


# ---------- the report ----------


def _subfinder(**kw) -> ProviderResult:
    return ProviderResult(source=SubdomainSource.SUBFINDER, **kw)


def test_each_source_counts_its_names_and_the_ones_only_it_found():
    sub = _subfinder(
        subdomains={"a.example.com", "b.example.com", "c.example.com", "out.other.com"},
        breakdown={
            "anubis": {"a.example.com", "B.EXAMPLE.COM."},
            "virustotal": {"a.example.com", "c.example.com", "out.other.com"},
        },
        source_stats={"virustotal": SourceStat(results=2, requests=3, errors=1)},
        keyed_sources={"virustotal": "virustotal", "shodan": "shodan"},
    )
    crt = ProviderResult(
        source=SubdomainSource.CRTNAME, subdomains={"a.example.com", "d.example.com"}
    )
    rows = {
        r["key"]: r
        for r in source_report(
            [sub, crt],
            ["a.example.com", "b.example.com", "c.example.com", "d.example.com"],
        )
    }
    assert rows["subfinder.virustotal"] | {} == {
        "key": "subfinder.virustotal",
        "label": "VirusTotal",
        "via": "subfinder",
        "names": 2,
        "only": 1,
        "status": SourceStatus.FOUND.value,
        "note": "1 failed request",
        "keyed": True,
    }
    assert rows["subfinder.anubis"]["names"] == 2
    assert rows["subfinder.anubis"]["only"] == 1
    assert rows["subfinder.shodan"]["status"] == SourceStatus.EMPTY.value
    assert rows["subfinder.shodan"]["label"] == "Shodan"
    assert rows["crtname"]["names"] == 2
    assert rows["crtname"]["only"] == 1


def test_a_keyed_source_that_only_failed_reads_failed():
    sub = _subfinder(
        source_stats={"censys": SourceStat(requests=1, errors=1)},
        keyed_sources={"censys": "censys"},
    )
    (row,) = source_report([sub], [])
    assert row["status"] == SourceStatus.FAILED.value
    assert row["note"] == "1 failed request"


def test_a_key_subfinder_skipped_is_named():
    sub = _subfinder(
        source_stats={"fofa": SourceStat(skipped=True)}, keyed_sources={"fofa": "fofa"}
    )
    (row,) = source_report([sub], [])
    assert row["status"] == SourceStatus.SKIPPED.value


def test_a_keyless_source_with_nothing_kept_is_left_out():
    sub = _subfinder(
        subdomains={"x.other.com"},
        breakdown={"rapiddns": {"x.other.com"}},
        source_stats={"commoncrawl": SourceStat(requests=2, errors=1)},
    )
    assert source_report([sub], []) == []


def test_a_skipped_or_failed_provider_is_one_row():
    rows = source_report(
        [
            ProviderResult(
                source=SubdomainSource.TLSX,
                skipped=True,
                skip_reason="tlsx not installed",
            ),
            ProviderResult(source=SubdomainSource.CTFR, error="crt.sh timed out"),
        ],
        [],
    )
    assert [(r["key"], r["status"], r["note"]) for r in rows] == [
        ("ctfr", SourceStatus.FAILED.value, "crt.sh timed out"),
        ("tlsx", SourceStatus.SKIPPED.value, "tlsx not installed"),
    ]


def test_rows_are_ordered_by_names():
    sub = _subfinder(
        subdomains={"a.example.com", "b.example.com"},
        breakdown={
            "thc": {"a.example.com"},
            "anubis": {"a.example.com", "b.example.com"},
        },
    )
    rows = source_report([sub], ["a.example.com", "b.example.com"])
    assert [r["label"] for r in rows] == ["anubis", "thc"]


def test_the_report_survives_json():
    sub = _subfinder(
        subdomains={"a.example.com"},
        breakdown={"anubis": {"a.example.com"}},
        keyed_sources={"virustotal": "virustotal"},
    )
    rows = source_report([sub], ["a.example.com"])
    assert json.loads(json.dumps(rows)) == rows


# ---------- the stage ----------


class _Stage:
    def __init__(self, results: list[ProviderResult], credentials: dict) -> None:
        stage = SubdomainStage.__new__(SubdomainStage)
        stage.session = None
        stage.ctx = SimpleNamespace(
            target_value="example.com",
            resolved=ResolvedScanConfig(
                target_value="example.com", target_type="domain"
            ),
            recorder=None,
            is_aborted=None,
        )
        stage.cfg = SubdomainConfig(passive_tools=["subfinder"])
        stage.transport = Transport(
            tool="dnsx", rate=None, threads=30, timeout=5, retries=0
        )
        stage._prefetch_keys = lambda: credentials
        stage._select_providers = lambda _cfg: []
        stage._run_providers = lambda _classes, pctx, **_kw: self._run(pctx, results)
        stage._infostealer_names = lambda: None
        stage._wildcard_profile = lambda _domain: _Wildcard()
        stage._expand = lambda *_args: []
        stage._write_names = lambda merged: len(merged)
        stage._resolve = lambda names, _wildcard=None: _Resolution(submitted=len(names))
        stage._persist = lambda *_args: (0, set())
        stage.emit_progress = lambda *_a, **_kw: None
        self.stage = stage
        self.pctx: ProviderContext | None = None

    def _run(self, pctx, results):
        self.pctx = pctx
        return results


def test_the_stage_hands_keys_and_accounts_to_its_providers_and_reports_sources():
    credentials = {
        "virustotal": ("vt", None),
        "fofa": ("fk", {"email": "a@b.co"}),
    }
    sub = _subfinder(
        subdomains={"a.example.com"},
        breakdown={"virustotal": {"a.example.com"}},
        keyed_sources={"virustotal": "virustotal", "fofa": "fofa"},
        cut_short=True,
        note="stopped at its 5-minute budget",
    )
    run = _Stage([sub], credentials)
    counts = run.stage.run().counts

    assert run.pctx.api_keys == {"virustotal": "vt", "fofa": "fk"}
    assert run.pctx.key_meta == {"virustotal": None, "fofa": {"email": "a@b.co"}}
    rows = {r["key"]: r for r in counts[SOURCES_KEY]}
    assert rows["subfinder.virustotal"]["names"] == 1
    assert rows["subfinder.fofa"]["status"] == SourceStatus.EMPTY.value
    assert counts[UNKEYED_KEY] == len(SUBFINDER_SOURCES) - 2
    assert counts[NOTE_KEY] == "Subfinder stopped at its 5-minute budget."


def test_no_unkeyed_count_when_subfinder_did_not_run():
    skipped = _subfinder(skipped=True, skip_reason="subfinder not installed")
    counts = _Stage([skipped], {}).stage.run().counts
    assert UNKEYED_KEY not in counts
    assert NOTE_KEY not in counts


def test_the_stage_prefetches_every_subfinder_key():
    assert {p.value for p in SUBFINDER_SOURCES} <= set(SubdomainStage.api_keys)
    assert {"netlas", "github", "chaos", "securitytrails"} <= set(
        SubdomainStage.api_keys
    )


# ---------- launch preview ----------


def _preview_warnings(stage: str, configured: set[str]) -> list[str]:
    from app.services.scan_engine.effects import _stage_status  # noqa: PLC0415
    from stages.registry import get_stage  # noqa: PLC0415

    spec = get_stage(stage)
    resolved = SimpleNamespace(
        stage=lambda _name: {"enabled": True},
        intensity="normal",
        target_type="domain",
        transports={},
    )
    warnings: list[str] = []
    _stage_status(spec, resolved, configured, set(spec.consumes), warnings)
    return warnings


def test_a_capability_with_no_key_set_warns_once():
    assert _preview_warnings("subdomain_discovery", set()) == [
        "Subdomain Discovery: no API key set. Reduced coverage."
    ]


def test_one_key_is_enough_to_silence_the_warning():
    assert _preview_warnings("subdomain_discovery", {"virustotal"}) == []


def test_a_support_stage_with_an_optional_key_never_warns():
    assert _preview_warnings("passive_ports", set()) == []


def _proxies(opener) -> dict:
    handler = next(
        h for h in opener.handlers if isinstance(h, urllib.request.ProxyHandler)
    )
    return handler.proxies


def test_a_keyed_source_takes_the_egress_proxy(monkeypatch):
    monkeypatch.setattr(provider_base, "egress_proxy", lambda: "http://egress:3128")
    provider = NetlasProvider(_ctx(proxy_url="http://burp:8080"))
    assert _proxies(provider._opener()) == {
        "http": "http://egress:3128",
        "https": "http://egress:3128",
    }


def test_a_keyless_source_falls_back_to_the_egress_proxy(monkeypatch):
    monkeypatch.setattr(provider_base, "egress_proxy", lambda: "http://egress:3128")
    assert _proxies(CtfrProvider(_ctx())._opener())["https"] == "http://egress:3128"
    scan = CtfrProvider(_ctx(proxy_url="http://burp:8080"))
    assert _proxies(scan._opener())["https"] == "http://burp:8080"
