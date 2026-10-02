from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.definitions.api_keys import API_PROVIDER_META
from shared.definitions.oast import DEFAULT_WAIT_SECONDS, EVICTION_SLACK
from shared.enums.api_key import APIProvider
from shared.services.scan_resolve import MASK, redact_command
from tools.nuclei.client import NucleiClient, NucleiOptions

pytestmark = pytest.mark.pipeline


def _args(**over) -> list[str]:
    return NucleiClient.args(
        SimpleNamespace(options=NucleiOptions(templates_file="templates.txt", **over))
    )


def _flag(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def test_without_oast_it_is_switched_off_entirely():
    assert "-no-interactsh" in _args(interactsh=False)


def test_the_listening_window_reaches_nuclei():
    args = _args(interactsh=True, oast_wait_seconds=300)
    assert _flag(args, "-interactions-cooldown-period") == "300"


def test_a_request_stays_correlatable_for_longer_than_we_listen():
    args = _args(interactsh=True, oast_wait_seconds=300)
    cooldown = int(_flag(args, "-interactions-cooldown-period"))
    eviction = int(_flag(args, "-interactions-eviction"))

    assert eviction > cooldown
    assert eviction == cooldown + EVICTION_SLACK


def test_no_window_leaves_nuclei_on_its_own_defaults():
    args = _args(interactsh=True, oast_wait_seconds=0)
    assert "-interactions-cooldown-period" not in args


def test_the_wait_is_paid_on_the_out_of_band_batch_alone():
    assert (
        _flag(
            _args(interactsh=True, oast_wait_seconds=0), "-interactions-cooldown-period"
        )
        is None
    )
    long = _args(interactsh=True, oast_wait_seconds=DEFAULT_WAIT_SECONDS)
    assert _flag(long, "-interactions-cooldown-period") == str(DEFAULT_WAIT_SECONDS)
    assert int(_flag(long, "-interactions-eviction")) > DEFAULT_WAIT_SECONDS


def test_the_token_reaches_nuclei():
    args = _args(
        interactsh=True, interactsh_server="oast.example.com", interactsh_token="t0k"
    )
    assert _flag(args, "-interactsh-token") == "t0k"


@pytest.mark.parametrize("token", [None, "", "   "])
def test_no_token_is_not_an_empty_token(token):
    args = _args(
        interactsh=True, interactsh_server="oast.example.com", interactsh_token=token
    )
    assert "-interactsh-token" not in args


def test_a_token_is_never_sent_when_oast_is_off():
    args = _args(interactsh=False, interactsh_token="t0k")
    assert "-interactsh-token" not in args


def test_the_token_has_somewhere_to_be_stored():
    assert APIProvider.INTERACTSH in API_PROVIDER_META
    assert API_PROVIDER_META[APIProvider.INTERACTSH]["requires_username"] is False


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
    redacted = redact_command(command)
    assert "SECRET" not in redacted
    assert MASK in redacted


def test_the_server_flag_is_left_alone():
    command = "nuclei -interactsh-server oast.example.com -u https://a.example.com"
    assert redact_command(command) == command
