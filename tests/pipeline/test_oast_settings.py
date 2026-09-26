from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shared.definitions.oast import (
    DEFAULT_WAIT_SECONDS,
    EVICTION_SLACK,
    OAST_BATCH_SECONDS,
    OAST_MODE_HELP,
    OAST_MODE_LABELS,
    OAST_TAG,
    OastConfig,
    OastMode,
    needs_callback,
    normalize_server,
    off_reason,
)
from shared.definitions.scan_surface import BATCH_SECONDS, ROOT_TIERS, Tier
from shared.models.instance_settings import InstanceSettings, oast_reason
from shared.services import oast as oast_settings
from shared.services.scan_surface import split, wants_callback
from stages.vulnerability_scan.scanners.base import Coverage
from stages.vulnerability_scan.scanners.nuclei import NucleiScanner
from stages.vulnerability_scan.stage import _planned_tiers

pytestmark = pytest.mark.pipeline


def _row(
    template_id: str,
    tags: list[str],
    requests: int = 1,
    *,
    needs_oast: bool = False,
    protocol: str = "http",
):
    return SimpleNamespace(
        id=template_id,
        template_id=template_id,
        tags=tags,
        protocol=protocol,
        paths=[],
        simple=False,
        requests=requests,
        severity="high",
        origin="official",
        needs_oast=needs_oast,
    )


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("oast.example.com", "oast.example.com"),
        ("https://oast.example.com/", "oast.example.com"),
        ("HTTP://OAST.Example.com/poll", "oast.example.com"),
        ("oast.example.com.", "oast.example.com"),
        ("not a host", None),
        ("localhost", None),
        ("", None),
        (None, None),
    ],
)
def test_a_server_is_read_as_a_bare_host(given, expected):
    assert normalize_server(given) == expected


def test_a_mode_that_cannot_be_used_says_why():
    assert off_reason(OastMode.OFF.value, server=None, acknowledged=True)
    assert off_reason(OastMode.SELF_HOSTED.value, server=None, acknowledged=True)
    assert (
        off_reason(OastMode.SELF_HOSTED.value, server="oast.x", acknowledged=False)
        is None
    )
    assert off_reason(OastMode.PUBLIC.value, server=None, acknowledged=False)
    assert off_reason(OastMode.PUBLIC.value, server=None, acknowledged=True) is None


def test_every_mode_is_labelled_and_explained():
    for mode in OastMode:
        assert OAST_MODE_LABELS[mode.value]
        assert OAST_MODE_HELP[mode.value]


def test_the_default_config_is_off_and_holds_no_token():
    config = OastConfig()
    assert config.mode == OastMode.OFF.value
    assert config.enabled is False
    assert config.token is None


def test_the_eviction_window_outlasts_the_wait():
    assert EVICTION_SLACK > 0


def test_the_out_of_band_checks_are_their_own_tier():
    rows = [
        _row("blind-ssrf", ["cve", "ssrf", OAST_TAG]),
        _row("log4shell", ["cve", "kev"], needs_oast=True),
        _row("plain-cve", ["cve", "geoserver"]),
        _row("env", ["exposure", "config"]),
    ]
    plan = split(rows)
    assert [r.template_id for r in plan.oast] == ["blind-ssrf", "log4shell"]
    assert [r.template_id for r in plan.product] == ["plain-cve"]
    assert all(not wants_callback(r) for r in plan.universal)
    assert plan.http_count == 4


def test_a_check_is_judged_on_what_it_references_not_its_tag():
    assert wants_callback(_row("tagged", [OAST_TAG]))
    assert wants_callback(_row("untagged", ["cve"], needs_oast=True))
    assert not wants_callback(_row("plain", ["cve"]))
    assert needs_callback('path: "{{BaseURL}}/?x={{interactsh-url}}"')
    assert needs_callback("part: interactsh_protocol")
    assert needs_callback(None, ["cve", OAST_TAG])
    assert not needs_callback("path: /login", ["cve"])


def test_a_service_check_that_needs_a_callback_keeps_its_own_protocol_lane():
    rows = [_row("net-oob", ["cve"], needs_oast=True, protocol="network")]
    plan = split(rows)
    assert [r.template_id for r in plan.services] == ["net-oob"], (
        "a network check in the http invocation runs against the wrong input"
    )
    assert not plan.oast


def test_an_origin_plans_the_out_of_band_tier():
    assert Tier.OAST.value in ROOT_TIERS


def test_an_origin_never_plans_a_tier_that_cannot_run():
    plan = split(
        [
            _row("blind-ssrf", ["cve", OAST_TAG]),
            _row("plain-cve", ["cve", "geoserver"]),
        ]
    )
    assert Tier.OAST.value in _planned_tiers(plan, True, heard=True)
    assert Tier.OAST.value not in _planned_tiers(plan, True, heard=False), (
        "a planned tier with no batches settles as scanned"
    )


def test_an_out_of_band_batch_sweeps_for_longer_so_the_wait_is_paid_less():
    assert OAST_BATCH_SECONDS > BATCH_SECONDS


def _scanner(oast: OastConfig, *, wanted: bool = True) -> NucleiScanner:
    """A scanner built by its constructor, reading `oast` as the instance setting."""
    ctx = SimpleNamespace(session=None, cfg=SimpleNamespace(interactsh=wanted))
    with patch.object(oast_settings, "config", return_value=oast):
        return NucleiScanner(ctx)


def test_the_tier_states_where_its_callbacks_go():
    scanner = _scanner(
        OastConfig(mode=OastMode.SELF_HOSTED.value, server="oast.acme.net")
    )
    assert scanner._heard is True
    note = scanner._callback_note()
    assert "oast.acme.net" in note
    assert f"waits {DEFAULT_WAIT_SECONDS}s" in note


def test_a_public_server_is_named_in_the_note():
    scanner = _scanner(OastConfig(mode=OastMode.PUBLIC.value))
    assert "ProjectDiscovery" in scanner._callback_note()


def test_the_scan_switch_alone_turns_the_tier_off():
    off_for_the_scan = _scanner(
        OastConfig(mode=OastMode.SELF_HOSTED.value, server="oast.acme.net"),
        wanted=False,
    )
    assert off_for_the_scan._heard is False
    assert "off for this scan" in off_for_the_scan._off_reason()

    unset = _scanner(OastConfig(reason="No self-hosted server is set."))
    assert unset._heard is False
    assert unset._off_reason() == "No self-hosted server is set."


def test_a_check_that_cannot_run_is_never_selected():
    rows = [
        _row("blind-ssrf", ["cve", OAST_TAG]),
        _row("log4shell", ["cve"], needs_oast=True),
        _row("plain-cve", ["cve"]),
    ]
    heard = _scanner(OastConfig(mode=OastMode.SELF_HOSTED.value, server="oast.x"))
    assert heard._selectable(rows) == (rows, 0)

    off = _scanner(OastConfig(reason="No self-hosted server is set."))
    kept, unheard = off._selectable(rows)
    assert [r.template_id for r in kept] == ["plain-cve"]
    assert unheard == 2, "nuclei refuses the request, so the check did not run"


def test_the_checks_that_could_not_run_get_one_row_that_says_so():
    off = _scanner(OastConfig(reason="No self-hosted server is set."))
    row = off._unheard_row(615)
    assert row.status == "skipped"
    assert row.tier is None, "it must not merge with the tier's batches"
    assert "615 checks need a callback and did not run." in row.error
    assert "No self-hosted server is set." in row.error


def test_the_note_lands_on_the_tier_rows_and_never_a_row_of_its_own():
    scanner = _scanner(
        OastConfig(mode=OastMode.SELF_HOSTED.value, server="oast.acme.net")
    )
    rows = [
        Coverage(group="Standard rate", tier=Tier.OAST.value, hosts_total=4),
        Coverage(group="Standard rate", tier=Tier.MATCHED.value, hosts_total=4),
    ]
    scanner._note_callbacks(rows)
    assert len(rows) == 2, "a second row would read as an invocation of its own"
    assert rows[0].error is not None
    assert "oast.acme.net" in rows[0].error
    assert rows[0].status == "completed"
    assert rows[1].error is None


def test_a_real_failure_on_a_tier_row_is_never_overwritten():
    scanner = _scanner(
        OastConfig(mode=OastMode.SELF_HOSTED.value, server="oast.acme.net")
    )
    row = Coverage(group="Standard rate", tier=Tier.OAST.value, hosts_total=4)
    row.error = "Stopped at the time budget. Remaining checks did not run."
    scanner._note_callbacks([row])
    assert row.error.startswith("Stopped at the time budget")


def test_the_instance_row_says_why_out_of_band_is_off():
    assert oast_reason(None) == off_reason(
        OastMode.OFF.value, server=None, acknowledged=False
    )
    unset = InstanceSettings(
        oast_mode=OastMode.SELF_HOSTED.value, oast_server="not a host"
    )
    assert unset.oast_host is None
    assert oast_reason(unset) == "No self-hosted server is set."
    hosted = InstanceSettings(
        oast_mode=OastMode.SELF_HOSTED.value, oast_server="https://OAST.Example.com/"
    )
    assert hosted.oast_host == "oast.example.com"
    assert oast_reason(hosted) is None
    public = InstanceSettings(oast_mode=OastMode.PUBLIC.value)
    assert public.oast_off_reason == "The public server has not been accepted."
