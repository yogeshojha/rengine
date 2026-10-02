from __future__ import annotations

import re
import uuid
from types import SimpleNamespace
from urllib.parse import urlsplit

from shared.definitions.watch import host_pattern
from shared.services.scope_filter import host_excluded
from stages.endpoint_probe.stage import EndpointProbeStage
from stages.url_discovery.providers.base import Host, UrlProvider
from stages.url_discovery.providers.katana import KatanaProvider, crawl_out_scope
from tools.katana.client import KatanaClient, url_pattern


def _resolved(**over):
    base = {
        "excluded_paths": [],
        "excluded_subdomains": [],
        "excluded_ips": [],
        "stages": {},
    }
    return SimpleNamespace(**{**base, **over})


class _Provider(UrlProvider):
    source = "test"

    def discover(self, _result) -> None:
        return None


def _provider(resolved) -> _Provider:
    hosts = [
        Host(url="http://10.1.2.3", host="10.1.2.3", port=80, scheme="http"),
        Host(url="http://[2001:db8::1]", host="2001:db8::1", port=80, scheme="http"),
    ]
    return _Provider(
        SimpleNamespace(hosts=hosts, apex_domains=["example.com"], resolved=resolved)
    )


def test_an_excluded_address_is_out_of_scope():
    provider = _provider(_resolved(excluded_ips=["10.0.0.0/8", "2001:db8::/32"]))
    assert not provider.in_scope("http://10.1.2.3/admin")
    assert not provider.in_scope("http://[2001:db8::1]/admin")
    assert provider.in_scope("https://www.example.com/")


def test_an_address_outside_the_exclusions_stays_in_scope():
    provider = _provider(_resolved(excluded_ips=["192.168.0.0/16"]))
    assert provider.in_scope("http://10.1.2.3/admin")


def test_an_excluded_host_is_out_of_scope():
    provider = _provider(_resolved(excluded_subdomains=["admin.example.com"]))
    assert not provider.in_scope("https://admin.example.com/")
    assert provider.in_scope("https://www.example.com/")


def test_an_address_pattern_never_matches_a_hostname():
    assert not host_excluded("www.example.com", [], ["10.0.0.0/8"])


def _stage(rows, resolved) -> EndpointProbeStage:
    stage = EndpointProbeStage.__new__(EndpointProbeStage)
    stage.ctx = SimpleNamespace(scan_id=uuid.uuid4(), resolved=resolved)
    stage.session = SimpleNamespace(
        execute=lambda _q: SimpleNamespace(all=lambda: rows)
    )
    return stage


def _row(url: str, host: str, path: str = "/"):
    return SimpleNamespace(url=url, host=host, path=path)


def test_the_probe_skips_endpoints_on_excluded_hosts_and_addresses():
    rows = [
        _row("https://admin.example.com/", "admin.example.com"),
        _row("http://10.1.2.3/", "10.1.2.3"),
        _row("https://www.example.com/", "www.example.com"),
    ]
    resolved = _resolved(
        excluded_subdomains=["admin.example.com"], excluded_ips=["10.0.0.0/8"]
    )
    assert _stage(rows, resolved)._pending(10) == ["https://www.example.com/"]


def test_the_probe_keeps_every_endpoint_with_no_exclusions():
    rows = [_row("https://admin.example.com/", "admin.example.com")]
    assert _stage(rows, _resolved())._pending(10) == ["https://admin.example.com/"]


def _matches(patterns: list[str], url: str) -> bool:
    return any(re.search(p, url) for p in patterns)


_CRAWLED = (
    "https://admin.example.com/",
    "http://user@xadmin.example.com:8080/x",
    "https://dev.example.com/login",
    "https://corp.example.com/",
    "https://a.corp.example.com?q=1",
    "https://www.example.com/admin",
    "https://dev.example.com.evil.net/",
    "https://dev.example.com@www.example.com/",
    "https://notcorp.example.com/",
)


def test_katana_skips_the_hosts_the_scope_filter_excludes():
    entries = [
        "admin",
        host_pattern("dev.example.com"),
        host_pattern("*.corp.example.com"),
    ]
    patterns = crawl_out_scope(entries)
    assert len(patterns) == len(entries)
    for url in _CRAWLED:
        host = urlsplit(url).hostname or ""
        assert _matches(patterns, url) == host_excluded(host, entries, []), url


def test_katana_leaves_globs_and_free_regexes_to_the_scope_filter():
    assert crawl_out_scope(["*staging*", r"^dev\d+\.", "a,b"]) == []


def _katana(apexes: list[str], hosts: list[str], scheme: str | None = None):
    rows = [Host(url=f"https://{h}", host=h, port=443, scheme="https") for h in hosts]
    return KatanaProvider(
        SimpleNamespace(
            hosts=rows,
            apex_domains=apexes,
            net=SimpleNamespace(probe_scheme=scheme),
        )
    )


def test_katana_stays_on_a_named_host_narrower_than_its_zone():
    patterns = _katana(
        ["app.example.com"], ["app.example.com", "other.net"], "https"
    )._crawl_in_scope()
    assert _matches(patterns, "https://app.example.com/x")
    assert _matches(patterns, "https://api.app.example.com:8443/")
    assert _matches(patterns, "https://other.net/")
    assert not _matches(patterns, "https://www.example.com/")
    assert not _matches(patterns, "https://example.com/")
    assert not _matches(patterns, "http://app.example.com/")
    assert not _matches(patterns, "https://app.example.com@evil.net/")


def test_katana_takes_no_in_scope_patterns_for_a_zone():
    assert _katana(["example.com"], ["www.example.com"])._crawl_in_scope() == []


def _katana_args(**over) -> list[str]:
    base = {
        "depth": 2,
        "threads": 10,
        "timeout": 10,
        "crawl_scope": "rdn",
        "max_duration_minutes": 0,
        "rate_limit": None,
        "include_js": False,
        "form_extraction": False,
        "ignore_query_params": False,
        "exclude_extensions": [],
        "headless": False,
        "proxy_url": None,
        "headers": {},
        "scheme": "https",
        "crawl_in_scope": [],
        "crawl_out_scope": [],
    }
    return KatanaClient._args(SimpleNamespace(**{**base, **over}))


def _values(args: list[str], flag: str) -> list[str]:
    return [args[i + 1] for i, arg in enumerate(args) if arg == flag]


def test_katana_in_scope_patterns_replace_the_bare_scheme():
    assert _values(_katana_args(), "-crawl-scope") == ["^https://"]
    pattern = url_pattern(r"app\.example\.com", "https")
    args = _katana_args(crawl_in_scope=[pattern], crawl_out_scope=["x"])
    assert _values(args, "-crawl-scope") == [pattern]
    assert _values(args, "-crawl-out-scope") == ["x"]
