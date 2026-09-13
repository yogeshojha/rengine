from __future__ import annotations

from pathlib import Path

import pytest

import tools.wafw00f.client as wafw00f
from tools.naabu.client import proxy_args

pytestmark = pytest.mark.pipeline


def _no_runner(*_args: object, **_kwargs: object) -> None:
    return None


@pytest.fixture
def waf_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(wafw00f, "CLIToolRunner", _no_runner)
    return wafw00f.Wafw00fClient


def test_naabu_takes_a_socks5_address_without_its_scheme():
    assert proxy_args("socks5://10.0.0.1:1080") == (["-proxy", "10.0.0.1:1080"], None)


def test_naabu_takes_credentials_in_their_own_flag():
    args, warning = proxy_args("socks5://u:p%40ss@10.0.0.1:1080")
    assert args == ["-proxy", "10.0.0.1:1080", "-proxy-auth", "u:p@ss"]
    assert warning is None


def test_a_bare_address_is_read_as_socks5():
    assert proxy_args("10.0.0.1:1080") == (["-proxy", "10.0.0.1:1080"], None)


@pytest.mark.parametrize(
    "proxy_url", ["http://10.0.0.1:8080", "https://p:8443", "http://u:p@10.0.0.1:8080"]
)
def test_a_proxy_naabu_cannot_use_is_named_rather_than_passed(proxy_url: str):
    args, warning = proxy_args(proxy_url)
    assert args == []
    assert warning is not None
    assert "socks5" in warning


def test_no_proxy_adds_no_flag():
    assert proxy_args(None) == ([], None)
    assert proxy_args("") == ([], None)


def test_wafw00f_writes_the_scan_headers_to_a_private_file(waf_client):
    client = waf_client(headers={"Authorization": "Bearer tok", "X-Env": "staging"})
    with client._header_file() as path:
        assert path is not None
        assert Path(path).read_text() == "Authorization: Bearer tok\nX-Env: staging\n"
        assert oct(Path(path).stat().st_mode & 0o777) == "0o600"
    assert not Path(path).exists()


def test_wafw00f_writes_no_file_when_the_scan_carries_no_header(waf_client):
    with waf_client()._header_file() as path:
        assert path is None
