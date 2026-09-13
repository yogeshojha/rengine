from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.ffuf.client import HEADER_FLAG as FFUF_HEADER
from tools.httpx.client import HEADER_FLAG as HTTPX_HEADER
from tools.katana.client import HEADER_FLAG as KATANA_HEADER
from tools.katana.client import KatanaClient
from tools.nuclei.client import HEADER_FLAG as NUCLEI_HEADER
from tools.nuclei.client import NucleiClient, NucleiOptions

pytestmark = pytest.mark.pipeline

# read off `<tool> -h` in the worker image on 2026-09-13
MEASURED = {
    "httpx": "-header",
    "nuclei": "-header",
    "katana": "-headers",
    "ffuf": "-H",
}


EMITTED = {
    "httpx": HTTPX_HEADER,
    "nuclei": NUCLEI_HEADER,
    "katana": KATANA_HEADER,
    "ffuf": FFUF_HEADER,
}


def test_each_client_emits_the_flag_its_tool_defines():
    assert EMITTED == MEASURED


def test_katana_does_not_borrow_the_httpx_spelling():
    assert KATANA_HEADER != HTTPX_HEADER


def _katana_args(headers: dict[str, str]) -> list[str]:
    return KatanaClient._args(
        SimpleNamespace(
            depth=2,
            threads=10,
            timeout=10,
            crawl_scope="rdn",
            max_duration_minutes=0,
            rate_limit=None,
            include_js=False,
            form_extraction=False,
            ignore_query_params=False,
            exclude_extensions=[],
            headless=False,
            proxy_url=None,
            headers=headers,
        )
    )


def test_katana_carries_the_scan_headers():
    args = _katana_args({"Authorization": "Bearer tok"})
    assert KATANA_HEADER in args
    assert args[args.index(KATANA_HEADER) + 1] == "Authorization: Bearer tok"


def test_katana_without_headers_names_no_header_flag():
    assert KATANA_HEADER not in _katana_args({})


def test_nuclei_carries_the_scan_headers():
    args = NucleiClient.args(
        SimpleNamespace(
            options=NucleiOptions(
                templates_file="t.txt", headers={"Authorization": "Bearer tok"}
            )
        )
    )
    assert args[args.index(NUCLEI_HEADER) + 1] == "Authorization: Bearer tok"
