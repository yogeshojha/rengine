"""Out-of-band testing: a callback that arrives after the scan must still be heard."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.enums.api_key import APIProvider
from shared.models.api_key import API_PROVIDER_META
from shared.services.scan_resolve import MASK, redact_command
from stages.vulnerability_scan.config import VulnerabilityScanConfig
from stages.vulnerability_scan.scanners.nuclei import NucleiScanner, _oast_server
from tools.nuclei.client import _EVICTION_SLACK, NucleiClient, NucleiOptions

pytestmark = pytest.mark.pipeline


def _args(**over) -> list[str]:
    return NucleiClient.args(
        SimpleNamespace(options=NucleiOptions(templates_file="templates.txt", **over))
    )


def _flag(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


# ── how long it keeps listening ──


def test_without_oast_it_is_switched_off_entirely():
    assert "-no-interactsh" in _args(interactsh=False)


def test_the_listening_window_reaches_nuclei():
    """nuclei gives up 5 seconds after its last request on its own."""
    args = _args(interactsh=True, oast_wait_seconds=300)
    assert _flag(args, "-interactions-cooldown-period") == "300"


def test_a_request_stays_correlatable_for_longer_than_we_listen():
    """A callback that outlives its request's cache entry has nothing to attach to."""
    args = _args(interactsh=True, oast_wait_seconds=300)
    cooldown = int(_flag(args, "-interactions-cooldown-period"))
    eviction = int(_flag(args, "-interactions-eviction"))

    assert eviction > cooldown
    assert eviction == cooldown + _EVICTION_SLACK


def test_no_window_leaves_nuclei_on_its_own_defaults():
    args = _args(interactsh=True, oast_wait_seconds=0)
    assert "-interactions-cooldown-period" not in args


def test_the_default_waits_minutes_not_seconds():
    assert VulnerabilityScanConfig().oast_wait_minutes >= 1


# ── the self-hosted server ──


def test_the_token_reaches_nuclei():
    args = _args(
        interactsh=True, interactsh_server="oast.example.com", interactsh_token="t0k"
    )
    assert _flag(args, "-interactsh-token") == "t0k"


@pytest.mark.parametrize("token", [None, "", "   "])
def test_no_token_is_not_an_empty_token(token):
    """An empty key row must not become `-interactsh-token ""`, which nuclei rejects."""
    args = _args(
        interactsh=True, interactsh_server="oast.example.com", interactsh_token=token
    )
    assert "-interactsh-token" not in args


def test_a_token_is_never_sent_when_oast_is_off():
    args = _args(interactsh=False, interactsh_token="t0k")
    assert "-interactsh-token" not in args


def test_the_token_is_not_even_read_when_oast_is_off():
    """Reading a secret you have no use for is a read that did not need to happen."""
    reads: list[str] = []
    scanner = NucleiScanner.__new__(NucleiScanner)
    scanner.ctx = SimpleNamespace(
        cfg=SimpleNamespace(
            threads=1,
            bulk_size=1,
            timeout=1,
            retries=0,
            max_host_error=1,
            max_minutes=0,
            headless=False,
            interactsh=False,
            interactsh_server="",
            oast_wait_minutes=5,
            honeypot_threshold=0,
        ),
        net=SimpleNamespace(proxy_url=None, headers={}),
        resolved=SimpleNamespace(follow_redirects=None, tool_args=lambda _t: []),
        session=None,
    )
    scanner._oast_token = lambda _ctx: reads.append("read") or "t0k"

    options = NucleiScanner._options(scanner, Path("t.txt"), 10)

    assert options.interactsh_token is None
    assert reads == [], "the key was fetched for a run that will not use it"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("oast.example.com", "oast.example.com"),
        ("https://oast.example.com", "oast.example.com"),
        ("http://oast.example.com/", "oast.example.com"),
        ("https://oast.example.com/path/x", "oast.example.com"),
        ("  oast.example.com.  ", "oast.example.com"),
    ],
)
def test_the_server_is_reduced_to_a_host(given: str, expected: str):
    """A scheme or a path makes nuclei register nowhere and fall back silently."""
    assert _oast_server(given) == expected


@pytest.mark.parametrize("given", ["", "   ", None, "https://"])
def test_nothing_configured_means_the_public_server(given):
    assert _oast_server(given) is None


def test_the_token_has_somewhere_to_be_stored():
    assert APIProvider.INTERACTSH in API_PROVIDER_META
    assert API_PROVIDER_META[APIProvider.INTERACTSH]["requires_username"] is False


# ── the token is a secret ──


@pytest.mark.parametrize(
    "command",
    [
        "nuclei -interactsh-token SECRET -u x",
        "nuclei -itoken SECRET -u x",
        "nuclei -itoken=SECRET",
        "nuclei --interactsh-token SECRET",
    ],
)
def test_every_spelling_of_the_token_flag_is_redacted(command: str):
    """A tool's choice of short flag must not decide whether a secret is stored."""
    redacted = redact_command(command)
    assert "SECRET" not in redacted
    assert MASK in redacted


@pytest.mark.parametrize(
    "command",
    [
        "naabu -timeout 3s -top-ports 100",
        "ffuf -w /tmp/w.txt:FUZZ -u https://a/FUZZ -maxtime 60",
        "nuclei -interactsh-server oast.example.com -u https://a.example.com",
    ],
)
def test_an_ordinary_flag_is_left_alone(command: str):
    assert redact_command(command) == command
