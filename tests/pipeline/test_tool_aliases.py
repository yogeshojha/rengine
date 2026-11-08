from __future__ import annotations

import pytest

from tools.httpx import client as httpx
from tools.katana import client as katana
from tools.nuclei import client as nuclei
from tools.runner.executor import merge_extra_args
from tools.tlsx import client as tlsx

pytestmark = pytest.mark.pipeline

# read off `<tool> -h` in yogeshojha/rengine-worker:3.0.0 on 2026-11-08
MEASURED = {
    "katana": {
        "-H": "-headers",
        "-u": "-list",
        "-o": "-output",
        "-j": "-jsonl",
        "-or": "-omit-raw",
        "-ob": "-omit-body",
        "-nc": "-no-color",
        "-kf": "-known-files",
        "-d": "-depth",
        "-c": "-concurrency",
        "-fs": "-field-scope",
        "-cs": "-crawl-scope",
        "-cos": "-crawl-out-scope",
        "-ct": "-crawl-duration",
        "-rl": "-rate-limit",
        "-jsl": "-jsluice",
        "-jc": "-js-crawl",
        "-aff": "-automatic-form-fill",
        "-iqp": "-ignore-query-params",
        "-ef": "-extension-filter",
        "-hl": "-headless",
        "-scp": "-system-chrome-path",
    },
    "tlsx": {
        "-c": "-concurrency",
        "-l": "-list",
        "-o": "-output",
        "-j": "-json",
        "-ex": "-expired",
        "-ss": "-self-signed",
        "-ro": "-resp-only",
    },
}

ALIASES = {
    "katana": katana.KATANA_ALIASES,
    "tlsx": tlsx.TLSX_ALIASES,
}

# measured pairs each map must hold
REQUIRED = {
    "httpx": {
        "-http-proxy": "-proxy",
        "-rl": "-rate-limit",
        "-t": "-threads",
        "-H": "-header",
        "-fr": "-follow-redirects",
        "-nfs": "-no-fallback-scheme",
        "-srd": "-store-response-dir",
    },
    "nuclei": {
        "-hpd": "-honeypot-detect",
        "-hpt": "-honeypot-threshold",
        "-shp": "-suppress-honeypot",
        "-rl": "-rate-limit",
        "-c": "-concurrency",
        "-p": "-proxy",
    },
}

MAPS = {
    "httpx": httpx.HTTPX_ALIASES,
    "nuclei": nuclei.NUCLEI_ALIASES,
}


@pytest.mark.parametrize("tool", sorted(MEASURED))
def test_alias_map_matches_the_tool_help(tool):
    assert ALIASES[tool] == MEASURED[tool]


@pytest.mark.parametrize("tool", sorted(REQUIRED))
def test_alias_map_holds_the_measured_pairs(tool):
    assert REQUIRED[tool].items() <= MAPS[tool].items()


class _Runner:
    def __init__(self, binary, **kwargs):
        self.binary = binary
        self.kwargs = kwargs


def test_katana_runner_carries_the_alias_map(monkeypatch):
    monkeypatch.setattr(katana, "CLIToolRunner", _Runner)
    client = katana.KatanaClient()
    assert client._runner.kwargs["aliases"] is katana.KATANA_ALIASES


def test_tlsx_runner_carries_the_alias_map(monkeypatch):
    monkeypatch.setattr(tlsx, "CLIToolRunner", _Runner)
    client = tlsx.TlsxClient()
    assert client._runner.kwargs["aliases"] is tlsx.TLSX_ALIASES


def test_httpx_long_proxy_spelling_does_not_replace_the_scan_proxy():
    args = ["-proxy", "socks5://192.0.2.1:1080"]
    extra = ["-http-proxy", "http://192.0.2.2:8080", "-sd"]
    assert merge_extra_args(args, extra, aliases=httpx.HTTPX_ALIASES) == ["-sd"]


def test_katana_short_rate_flag_does_not_restate_the_ceiling():
    args = ["-rate-limit", "5", "-concurrency", "10", "-depth", "3"]
    extra = ["-rl", "9999", "-c", "200", "-d", "9", "-tech-detect"]
    assert merge_extra_args(args, extra, aliases=katana.KATANA_ALIASES) == [
        "-tech-detect"
    ]
